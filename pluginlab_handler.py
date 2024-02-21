from pluginlab_admin import App


class PluginLabHandler:
    def __init__(self, secret_key: str, plugin_id: str, message_handler):
        print("Initializing PluginLabHandler")
        self.app = App(secret_key=secret_key, plugin_id=plugin_id)
        self.auth = self.app.get_auth()
        self.message_handler = message_handler

    def get_token_from_request(self, request):
          auth_header = request.headers.get('Authorization')
          if auth_header and auth_header.startswith('Bearer '):
              token = auth_header.split(' ')[1] 
              #print(f"Token retrieved from request: {token}")
              return token
          #print("No token found in request")
          return None
      
      
  
    def get_user_data_from_token(self, token: str):
      try:
          verified_token = self.auth.verify_token(token)
          print(f"verified_token: {verified_token}")
          uid = verified_token.uid  # Accessing the uid attribute
          member = self.auth.get_member_by_id(uid)
          identities = self.auth.get_member_identities(uid)
          if identities.github:
              github_access_token = identities.github.access_token
          else:
              github_access_token = None  
          user_data = {
              "ID" : member.id,
              "email": member.auth.email,
              "name": member.name,
              "given_name": member.given_name,
              "family_name": member.family_name,
              "plan_id": verified_token.user.plan_id,
              "price_id": verified_token.user.price_id,
              "github_token": github_access_token
              
          }
          print(f"User data retrieved: {user_data}")
          return user_data, None
      except Exception as e:
          print(f"Error getting user data from token: {e}")
          return None, str(e)
