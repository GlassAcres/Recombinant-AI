# rider_middleware/current_project.py

from supabase_py import Client

def get_settings(user_id: str, supabase: Client):
    #print("[CurrentProject] Fetching most recent project...")
    
    try:
        # Fetch the most recently accessed project for the user based on "Last Active"
        response = supabase.table('Settings')\
            .select("Tone", "system_message", "current_task")\
            .filter('ID', 'eq', user_id)\
            .limit(1)\
            .execute()
        print(response)


        # Extract the project_id from the response
        settings = response.get('data', [])
        if settings:
            Tone = settings[0].get('Tone')
            system_message = settings[0].get("system_message")
            current_task = settings[0].get("current_task")
            return Tone, system_message, current_task
          
        return None

    except Exception as e:
        print(f"[CurrentProject] Error fetching settings for user {user_id}: {e}")
        return None
