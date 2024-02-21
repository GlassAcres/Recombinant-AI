import uuid
from pydantic import BaseModel
from typing import Optional, List, Dict, Union
from fastapi import HTTPException, Depends, Request
from datetime import datetime
from pluginlab_handler import PluginLabHandler
from supabase_handler import SupabaseHandler
from json.decoder import JSONDecodeError

FileContent = Dict[str, Union[
    str,  # For raw content like simple notes or descriptions
    List[str],  # For lines of code, comments, or bullet-point notes
    Dict[str, str],  # For key-value pairs, e.g., metadata or simple key-value notes
    List[Dict[str, Union[str, List[str]]]],  # For structured content like functions, classes, or grouped notes
    Dict[str, List[str]]  # For sections or categories of notes
]]

class File(BaseModel):
    file_name: Optional[str]
    project_id: Optional[str]
    file_type: Optional[str]
    file_content: List[Optional[str]               ]

class Project(BaseModel):
    Project_name: Optional[str]
    Summary: Optional[str]
    repos_referenced: Optional[List[str]]
    Packages: Optional[List[str]]
    Files: Optional[List[str]]
    Goal: Optional[str]


class FileHandler:

    @staticmethod
    async def get_current_user_data(request: Request, pluginlab_handler: PluginLabHandler):
        print("[DEBUG] Entering get_current_user_data method.")
        try:
            print("[DEBUG] Attempting to retrieve token from request.")
            token = pluginlab_handler.get_token_from_request(request)
            print(f"[DEBUG] Token retrieved: {token[:10]}... (truncated for brevity)")

            print("[DEBUG] Attempting to retrieve user data from token.")
            user_data, _ = pluginlab_handler.get_user_data_from_token(token)
            print(f"[DEBUG] User data retrieved: {user_data}")

            return user_data
        except Exception as e:
            print(f"[ERROR] Exception in get_current_user_data: {e}")
            raise HTTPException(status_code=401, detail=f"Unable to retrieve user data. Exception: {e}")

    @staticmethod
    async def create_file(file: File, supabase, message_handler, request: Request, pluginlab_handler: PluginLabHandler):
        print("[DEBUG] Entering create_file method.")
        
        user_data = await FileHandler.get_current_user_data(request, pluginlab_handler)
        print("[DEBUG] Entering create_file method.")
        try:
            print("[DEBUG] Preparing file data for insertion.")
            file_data = file.dict()
            file_data["file_id"] = str(uuid.uuid4())
            file_data["ID"] = user_data["ID"]
            file_data["email"] = user_data["email"]
            file_data["created_at"] = datetime.now().isoformat()
            file_data["last_active"] = datetime.now().isoformat()
            print(f"[DEBUG] File data prepared: {file_data}")

            print("[DEBUG] Attempting to insert file data into database.")
            result = supabase.table('File').insert(file_data).execute()
            print(f"[DEBUG] Database insertion result: {result}")

            if 'data' not in result:
                print(f"[ERROR] Unexpected result structure from database: {result}")
                raise ValueError("Unexpected result structure from the database.")

            file_id = result['data'][0]['file_id']
            print(f"[DEBUG] File {file_id} created successfully.")
            return {"status": "success", "message": "File created!", "file_id": file_id}
        except Exception as e:
            print(f"[ERROR] Exception in create_file: {e}")
            raise HTTPException(status_code=500, detail=f"Exception during file creation: {e}")

             
    @staticmethod
    async def get_files_by_user_id(user_id: str, supabase):
        print(f"[DEBUG] Entering get_files_by_user_id method for user_id: {user_id}.")
        try:
            print("[DEBUG] Attempting to retrieve file data from database by user ID.")
            response = supabase.table('File').select("*").filter('ID', 'eq', user_id).execute()
            print(f"[DEBUG] File data retrieved: {response}")

            files = response.get('data', [])

            if not files:
                print(f" User Id not found {user_id}")
                return []
            

            return files
        except Exception as e:
            print(f"[ERROR] Exception in get_files_by_user_id: {e}")
            raise HTTPException(status_code=500, detail=f"Exception during get_files_by_user_id: {e}")

  
    @staticmethod
    async def update_file(file_id: str, updated_data: File, supabase):
        print(f"[DEBUG] Entering update_file method for file_id: {file_id}.")
        
        # Fetch existing file data
        existing_file_data = supabase.table('File').select('*').filter('file_id', 'eq', file_id).execute().get('data')
        
        if not existing_file_data:
            # If file doesn't exist, return an error message
            return {"status": "error", "message": f"File with ID {file_id} not found."}
        
        # Update the necessary fields in the fetched data with the new updated_data
        try:
            data_dict = updated_data.dict(exclude_unset=True)
            
            # If file_content is empty or not provided, exclude it from the update
            if not data_dict.get('file_content'):
                data_dict.pop('file_content', None)
            
            for key, value in data_dict.items():
                existing_file_data[0][key] = value
            print(f"Updated file data: {existing_file_data[0]}")
        except Exception as e:
            print(f"[ERROR] Exception when updating file data: {e}")
            raise HTTPException(status_code=500, detail=f"Error updating file data: {e}")
        
        try:
            print("[DEBUG] Attempting to update file data in database.")
            result = supabase.table('File').insert(existing_file_data[0], upsert=True).execute()
    
            print(f"[DEBUG] File update result: {result}")
            
            # Check if the update was successful
            if not result or 'error' in result:
                error_message = result.get('error', 'Unknown error during file update')
                print(f"[ERROR] Error during file update: {error_message}")
                raise HTTPException(status_code=500, detail=error_message)
            
            return {"status": "success", "message": f"File {file_id} updated!"}
        except Exception as e:
            print(f"[ERROR] Exception in update_file: {e}")
            raise HTTPException(status_code=500, detail=f"Exception during update_file: {e}")
    
        
    
    staticmethod
    async def delete_file(file_id: str, supabase, message_handler, request: Request):
        try:
            # Fetch the initial state of the file
            initial_state = supabase.table('File').select("*").eq('file_id', file_id).execute()
            print(f"Initial state for file {file_id}: {initial_state}")

            # Check if the file exists
            if not initial_state['data']:
                print(f"No file found with ID {file_id}.")
                return {"status": "failure", "message": f"File {file_id} does not exist."}

            # Delete the file
            response = supabase.table('File').delete().eq('file_id', file_id).execute()
            
            # Check if the response is empty or None (indicating a successful delete)
            if not response or response.get('data') is None:
                print(f"File {file_id} deleted successfully.")
                await message_handler.print_and_store(f"File {file_id} deleted successfully.", request)
                return {"status": "success", "message": f"File {file_id} deleted!"}
            else:
                print(f"Failed to delete file {file_id}.")
                return {"status": "failure", "message": f"Failed to delete file {file_id}."}

            # Check the response
            if response.get('data'):
                print(f"File {file_id} deleted successfully.")
                await message_handler.print_and_store(f"File {file_id} deleted successfully.", request)
                return {"status": "success", "message": f"File {file_id} deleted!"}
            else:
                print(f"Failed to delete file {file_id}.")
                return {"status": "failure", "message": f"Failed to delete file {file_id}."}

        except JSONDecodeError as e:
            print(f"JSONDecodeError occurred: {e}")
            raise HTTPException(status_code=200, detail="File Deleted!.")
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_files_by_project(project_id: str, supabase):
        print(f"[DEBUG] Entering get_files_by_project method for project_id: {project_id}.")
        try:
            print("[DEBUG] Attempting to retrieve files associated with the project from database.")
            response = supabase.table('File').select("*").eq('project_id', project_id).execute()
            print(f"[DEBUG] Files retrieved: {response}")
    
            return response.get('data', [])
        except Exception as e:
            print(f"[ERROR] Exception in get_files_by_project: {e}")
            raise HTTPException(status_code=500, detail=f"Exception during get_files_by_project: {e}")
