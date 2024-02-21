import uuid
import traceback
from pydantic import BaseModel
from typing import Optional, List
from fastapi import HTTPException, Depends, Request
from datetime import datetime
import inspect
from pluginlab_handler import PluginLabHandler
from supabase_handler import SupabaseHandler
from json.decoder import JSONDecodeError


class Project(BaseModel):
    Project_name: str
    Summary: str
    repos_referenced: List[str]
    Packages: List[str]
    Files: List[str]
    Goal: str

class ProjectHandler:

    @staticmethod
    async def get_current_user_data(request: Request, pluginlab_handler: PluginLabHandler):
        print("Attempting to get current user data...")
        try:
            token = pluginlab_handler.get_token_from_request(request)
            user_data, _ = pluginlab_handler.get_user_data_from_token(token)
            print(f"Retrieved user data: {user_data}")
            return user_data
        except Exception as e:
            print(f"Error retrieving user data: {e}")
            raise HTTPException(status_code=401, detail="Unable to retrieve user data.")

    @staticmethod
    async def create_project(project: Project, supabase, message_handler, request: Request, user_data: dict = Depends(get_current_user_data)):
        print("Starting project creation")
        try:
            project_data = project.dict()
            project_data["ID"] = user_data["ID"]
            project_data["project_id"] = str(uuid.uuid4())
            project_data["created_at"] = datetime.now().isoformat()
            project_data["Last Active"] = datetime.now().isoformat()
            project_data["email"] = user_data["email"]   
            print(f"[STATUS]:, {project_data}")
            print("Attempting to add project to the database.")
            result = supabase.table('Project').insert(project_data).execute()
            print(result)
            
            # Check if 'data' key exists in the result
            if 'data' not in result:
                print(f"Unexpected result structure: {result}")
                raise ValueError("Unexpected result structure from the database.")
            
            # Print out the result['data'] to see its structure
            print(f"Result Data: {result['data']}")
    
            # Check if result['data'] is a list and has at least one item
            if not isinstance(result['data'], list) or len(result['data']) == 0:
                print(f"Unexpected data format: {result['data']}")
                raise ValueError("Unexpected data format from the database.")
              
            project_id = result['data'][0]['project_id']
            print(f"Project {project_id} created successfully.")
            #message_handler.print_and_store(f"Project {project_id} created successfully.", request)  # Pass the request object here
            return {"status": "success", "message": "Project created!", "project_id": project_id}
        
        except Exception as e:
                print(f"Error occurred while creating project: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                return {"status": "error", "message": "An error occurred while creating the project."}


    
   
    @staticmethod
    async def update_project(project_id: str, updated_data: Project, supabase, message_handler, request: Request):
        print(f"[DEBUG] Entering update_project method for project_id: {project_id}.")
        
        # Check the type and value of project_id
        print(f"Type of project_id: {type(project_id)}, Value: {project_id}")
        
        # Fetch existing project data
        existing_project_data = supabase.table('Project').select('*').filter('project_id', 'eq', project_id).execute().get('data')
        
        if not existing_project_data:
            # If project doesn't exist, ask the user if they want to create a new project
            return {"status": "info", "message": f"Project with ID {project_id} not found. Do you want to create a new project with the provided information?"}
        
        # Update the necessary fields in the fetched data with the new updated_data
        try:
            data_dict = updated_data.dict()
            for key, value in data_dict.items():
                existing_project_data[0][key] = value
            existing_project_data[0]['Last Active'] = datetime.now().isoformat()
            print(f"Updated project data: {existing_project_data[0]}")
        except Exception as e:
            print(f"[ERROR] Exception when updating project data: {e}")
            raise HTTPException(status_code=500, detail=f"Error updating project data: {e}")
        
        try:
            print("[DEBUG] Attempting to update project data in database.")
            result = supabase.table('Project').insert(existing_project_data[0], upsert=True).execute()
    
            print(f"[DEBUG] Project update result: {result}")
            
            # Check if the update was successful
            if not result or 'error' in result:
                error_message = result.get('error', 'Unknown error during project update')
                print(f"[ERROR] Error during project update: {error_message}")
                raise HTTPException(status_code=500, detail=error_message)
            
            return {"status": "success", "message": f"Project {project_id} updated!"}
        except Exception as e:
            print(f"[ERROR] Exception in update_project: {e}")
            raise HTTPException(status_code=500, detail=f"Exception during update_project: {e}")


    

    @staticmethod
    async def delete_project(project_id: str, supabase, message_handler, request: Request):
        try:
            # Fetch the initial state of the project
            initial_state = supabase.table('Project').select("*").eq('project_id', project_id).execute()
            print(f"Initial state for project {project_id}: {initial_state}")

            # Check if the project exists
            if not initial_state['data']:
                print(f"No project found with ID {project_id}.")
                return {"status": "failure", "message": f"Project {project_id} does not exist."}

            # Delete the project
            # Delete the project
            response = supabase.table('Project').delete().eq('project_id', project_id).execute()
            
            # Check if the response is empty or None (indicating a successful delete)
            if not response or response.get('data') is None:
                print(f"Project {project_id} deleted successfully.")
                await message_handler.print_and_store(f"Project {project_id} deleted successfully.", request)
                return {"status": "success", "message": f"Project {project_id} deleted!"}
            else:
                print(f"Failed to delete project {project_id}.")
                return {"status": "failure", "message": f"Failed to delete project {project_id}."}

            # Check the response
            if response.get('data'):
                print(f"Project {project_id} deleted successfully.")
                await message_handler.print_and_store(f"Project {project_id} deleted successfully.", request)
                return {"status": "success", "message": f"Project {project_id} deleted!"}
            else:
                print(f"Failed to delete project {project_id}.")
                return {"status": "failure", "message": f"Failed to delete project {project_id}."}

        except JSONDecodeError as e:
            print(f"JSONDecodeError occurred: {e}")
            raise HTTPException(status_code=200, detail="Project Deleted!.")
        except Exception as e:
            print(f"Error deleting project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 
    
    
    
    @staticmethod
    async def get_projects_by_user(user_id: str, supabase, message_handler):
        print(f"Starting: Attempting to fetch projects for User ID {user_id}...")
        try:
            # Fetch projects for the user
            print("Step 1: Fetching projects from the database...")
            response = supabase.table('Project').select("*").filter('ID', 'eq', user_id).execute()

            
            # Log the type and content of the response
            print(f"Type of response: {type(response)}")
            print(f"Response content: {response}")
            
            # Extract the list of projects from the response
            projects = response.get('data', [])
            
            # Log the type and content of the projects
            print(f"Type of projects: {type(projects)}")
            print(f"Projects content: {projects}")
        
            if not projects:
                print(f"Warning: No projects found for User ID {user_id}.")
                return []
        
            print(f"Success: Fetched {len(projects)} projects for User ID {user_id}.")
            return projects
        
        except Exception as e:
            print(f"Critical Error: An exception occurred while fetching projects: {e}")
            return None
