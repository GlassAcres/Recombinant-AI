# rider_middleware/middleware.py

from .current_project import get_most_recent_project
from .current_settings import get_settings


async def current_data_middleware(request, call_next, supabase):
    if 'user_data' in request.scope and request.scope['user_data']:
        user_id = request.scope['user_data']['ID']
        

        # Fetch most recent project
        project_result = get_most_recent_project(user_id, supabase)
        if project_result:
            current_project_id, current_project_name, Files = project_result
            request.scope['current_project_id'] = current_project_id
            request.scope['current_project_name'] = current_project_name
        else:
            request.scope['current_project_id'] = None
            request.scope['current_project_name'] = None

        # Fetch most recent settings
        setting_result = get_settings(user_id, supabase)
        if setting_result:
            Tone, system_message, current_task = setting_result
            request.scope['Tone'] = Tone
            request.scope['system_message'] = system_message
            request.scope['current_task'] = current_task
        else:
            request.scope['Tone'] = None
            request.scope['system_message'] = None
            request.scope['current_task'] = None

    response = await call_next(request)
    return response
