from social_core.backends.oauth import BaseOAuth2
from social_core.utils import handle_http_errors


class TapisOAuth2(BaseOAuth2):
    name = "tapis"

    DEFAULT_TENANT_ID = "tacc"

    @property
    def AUTHORIZATION_URL(self):
        """Generate authorization URL based on tenant ID setting"""
        tenant = self.setting("TENANT_ID", self.DEFAULT_TENANT_ID)
        return f"https://{tenant}.tapis.io/v3/oauth2/authorize"

    @property
    def ACCESS_TOKEN_URL(self):
        """Generate access token URL based on tenant ID setting"""
        tenant = self.setting("TENANT_ID", self.DEFAULT_TENANT_ID)
        return f"https://{tenant}.tapis.io/v3/oauth2/tokens"

    @property
    def USERINFO_URL(self):
        """Generate user info URL based on tenant ID setting"""
        tenant = self.setting("TENANT_ID", self.DEFAULT_TENANT_ID)
        return f"https://{tenant}.tapis.io/v3/oauth2/userinfo"

    ACCESS_TOKEN_METHOD = "POST"
    REDIRECT_STATE = False  # Don't include state parameter since tapis validates redirect_uri and state invalidates it?
    RESPONSE_TYPE = "code"
    USE_BASIC_AUTH = True

    # Upstream this is initialized to None, but it is expected this will be a list of tuples
    EXTRA_DATA = [
        ("refresh_token", "refresh_token"),
    ]

    def get_user_id(self, details, response):
        """
        Return a unique ID for the current user.
        We create a tenant-scoped unique identifier to handle multiple tenants.
        """
        username = response.get("username")
        tenant = self.setting("TENANT_ID", self.DEFAULT_TENANT_ID)
        # Create a unique identifier that includes both tenant and username
        # This ensures users from different tenants don't collide
        user_id = f"{tenant}:{username}"
        return user_id

    def get_user_details(self, response):
        """
        Extract user details from the Tapis API response.
        """
        # For TACC Tapis, we use username@tacc.utexas.edu as the email, but this may vary by deployment
        # TODO: We may want to eventually allow config override of canonical identifier for username/email, if needed.
        # For now, with TACC Tapis, we will hardcode the domain to `tacc.utexas.edu` for email addresses.
        TAPIS_DOMAIN_OVERRIDE = "tacc.utexas.edu"
        username = response.get("username")
        user_details = {
            "username": username,
            "email": f"{username}@{TAPIS_DOMAIN_OVERRIDE}",
        }
        return user_details

    def user_data(self, access_token, *args, **kwargs):
        """
        Fetch user profile data from Tapis API.

        This uses the access token to retrieve the user's profile information
        from the Tapis API endpoint.
        """
        # Set up the authorization header with the access token
        headers = {"X-Tapis-Token": f"{access_token.get('access_token', '')}"}

        # Make the request to the profile endpoint
        response = self.get_json(self.USERINFO_URL, headers=headers)

        # If the response is in a nested structure, extract the user data
        # This may need adjustment based on the actual Tapis API response structure
        if response and isinstance(response, dict):
            # If the result is nested inside a 'result' key, extract it
            user_data = response.get("result", response)
            return user_data

        return response

    @handle_http_errors
    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        self.process_error(self.data)
        state = self.validate_state()

        data = self.auth_complete_params(state)

        response = self.request_access_token(
            self.access_token_url(),
            data=data,
            params=None,
            headers=self.auth_headers(),
            auth=self.auth_complete_credentials(),
            method=self.ACCESS_TOKEN_METHOD,
        )
        self.process_error(response)
        result = response.get("result")
        if not result:
            raise ValueError("No result found in Tapis authentication response")
        token = result.get("access_token")
        if not token:
            raise ValueError("No access token found in Tapis authentication response")
        # ignore B026, we keep the same signature as the base class
        return self.do_auth(token, response=response, *args, **kwargs)  # noqa: B026

    def restructure_response(self, response):
        # For compatibility we pull several keys up to the top to match the expected payload
        if "access_token" in response.get("result", {}).get("access_token", {}):
            response["access_token"] = response["result"]["access_token"]["access_token"]

        if "id_token" in response.get("result", {}).get("access_token", {}):
            response["id_token"] = response["result"]["access_token"]["id_token"]

        if "refresh_token" in response.get("result", {}):
            response["refresh_token"] = response["result"]["refresh_token"]
        return response

    @handle_http_errors
    def do_auth(self, access_token, *args, **kwargs):
        """Finish the auth process once the access_token was retrieved"""
        data = self.user_data(access_token, *args, **kwargs)
        response = kwargs.get("response") or {}
        response.update(data or {})
        # Restructure response to pop access_token, id_token, and refresh_token up.
        response = self.restructure_response(response)
        kwargs.update({"response": response, "backend": self})
        return self.strategy.authenticate(*args, **kwargs)
