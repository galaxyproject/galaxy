"""Manager for the OAuth 2.0 device flow, which lets an external app log in to Galaxy for a user."""

from dataclasses import dataclass

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.api_keys import ApiKeyManager

# Apps allowed to start a device flow login, by client ID, with the name shown on the approval page.
# (Later, we can add apps like `galaxy-mcp` etc.)
KNOWN_APPS: dict[str, str] = {
    "galaxy-cli": "Galaxy CLI",
}


@dataclass
class IssuedToken:
    access_token: str
    # Seconds until the token expires, or None if it does not expire.
    expires_in: int | None
    scope: str | None


class OAuthDeviceManager:
    def __init__(self, api_keys_manager: ApiKeyManager):
        self.api_keys_manager = api_keys_manager

    def get_app_name(self, client_id: str) -> str:
        """Return the display name of a known app, or raise if the client ID is not known."""
        name = KNOWN_APPS.get(client_id)
        if name is None:
            raise RequestParameterInvalidException(f"Unknown client_id '{client_id}'.")
        return name

    def issue_token(self, user: model.User, client_id: str, scope: str | None) -> IssuedToken:
        """Issue a token for a user who approved a device flow login.

        TODO: Placeholder until scoped, expiring tokens exist. For now, returns the user's API
              key, which ignores the scope and never expires. Must not ship as is.
        """
        return IssuedToken(
            access_token=self.api_keys_manager.get_or_create_api_key(user),
            expires_in=None,
            scope=scope,
        )
