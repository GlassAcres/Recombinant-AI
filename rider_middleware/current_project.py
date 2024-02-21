# rider_middleware/current_project.py

from supabase_py import Client

def get_most_recent_project(user_id: str, supabase: Client):
    print("Getting POJECTS")
    #print("[CurrentProject] Fetching most recent project...")
    
    try:
        # Fetch the most recently accessed project for the user based on "Last Active"
        response = supabase.table('Project')\
            .select("project_id", "Project_name", "Files")\
            .filter('ID', 'eq', user_id)\
            .order("Last Active", desc=False)\
            .limit(4)\
            .execute()
        print(response)


        # Extract the project_id from the response
        project_data = response.get('data', [])
        if project_data:
            project_id = project_data[0].get('project_id')
            Project_name = project_data[0].get("Project_name")
            Files = project_data[0].get("Files")
            return project_id, Project_name, Files
          
        return None

    except Exception as e:
        print(f"[CurrentProject] Error fetching most recent project for user {user_id}: {e}")
        return None
