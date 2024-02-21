from datetime import datetime
from supabase_py import Client
from pluginlab_handler import PluginLabHandler
import json

class SupabaseHandler:
    def __init__(self, supabase: Client, message_handler):
        print("[STATUS] Initialize Supabase Handler")
        self.supabase = supabase
        self.message_handler = message_handler

    async def check_user_exists(self, email: str, message_handler) -> bool:
        result = self.supabase.table('User_Data').select('email').filter('email', 'eq', email).execute()
        exists = bool(result and result.get('data'))
        return exists


    async def add_user_data(self, email, user_data: dict):
        user_data["created"] = datetime.now().isoformat()
        user_data["Messages"] = []
        response = self.supabase.table('User_Data').insert(user_data).execute()
        return response

    def store_message(self, email: str, content: dict, pluginlab_handler: PluginLabHandler, token: str):
        user_data = self.supabase.table('User_Data').select('ID, Messages').filter('email', 'eq', email).execute().get('data')
        if user_data:
            user_id = user_data[0]['ID']
            pluginlab_user_data, _ = pluginlab_handler.get_user_data_from_token(token)
            plan_id = pluginlab_user_data['plan_id']
            price_id = pluginlab_user_data['price_id']
            messages = user_data[0]['Messages'] if user_data[0]['Messages'] else []
            messages.append({"Message": content})
            messages = messages[-15:]
            data_to_insert = {
                "ID": user_id,
                "Messages": messages,
                "plan_id": plan_id,
                "price_id": price_id,
                "last_active": datetime.now().isoformat(),
            }
            response = self.supabase.table('User_Data').insert(data_to_insert, upsert=True).execute()
            return response
        else:
            return None

    async def fetch_messages(self, email):
        user_data = self.supabase.table('User_Data').select('ID, Messages').filter('email', 'eq', email).execute().get('data')
        if user_data:
            messages = user_data[0]['Messages'] if user_data[0]['Messages'] else []
            return messages
        else:
            return None


