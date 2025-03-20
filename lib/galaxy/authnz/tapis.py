from social_core.backends.oauth import BaseOAuth2


class TapisOAuth2(BaseOAuth2):
    name = "tapis"
    # TODO: parameterize tenant
    AUTHORIZATION_URL = "https://cfde.tapis.io/v3/oauth2/authorize"
    ACCESS_TOKEN_URL = "https://cfde.tapis.io/v3/oauth2/tokens"
    ACCESS_TOKEN_METHOD = "POST"
    REDIRECT_STATE = False  # Don't include state parameter since tapis validates redirect_uri and state invalidates it?

    RESPONSE_TYPE = "code"

    # What extra data do we need?
    EXTRA_DATA = [
        ("expires_in", "expires"),
        ("refresh_token", "refresh_token"),
    ]

    def get_user_details(self, response):
        """
        Extract user details from the Tapis API response.
        TODO: verify and adjust the field names as provided by Tapis.
        """
        return {
            "username": response.get("username"),
            "email": response.get("email"),
            "fullname": response.get("full_name"),
        }

    def user_data(self, access_token, *args, **kwargs):
        """
        If Tapis provides an endpoint for user profile info we need, we can
        fetch it here. Otherwise, return an empty dict.
        """
        # For example:
        # url = 'https://tacc.tapis.io/v3/profile'
        # response = self.get_json(url, params={'access_token': access_token})
        # return response
        return {}  # Modify this if you have a user data endpoint
