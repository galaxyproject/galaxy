from base64 import b64decode
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
    Union,
)
from urllib.parse import unquote

from pydantic import BaseModel
from starlette.requests import Request as StartletteRequest

from galaxy import exceptions
from galaxy.auth import AuthManager
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.users import UserManager
from galaxy.util import (
    smart_str,
    unicodify,
)
from galaxy.web.framework.base import Request as GxRequest

Request = Union[GxRequest, StartletteRequest]


class APIKeyResponse(BaseModel):
    api_key: str


class AuthenticationService:
    def __init__(self, user_manager: UserManager, auth_manager: AuthManager, api_keys_manager: ApiKeyManager):
        self._user_manager = user_manager
        self._auth_manager = auth_manager
        self._api_keys_manager = api_keys_manager

    def get_api_key(self, environ: Dict[str, Any], request: Request) -> APIKeyResponse:
        auth_header = environ.get("HTTP_AUTHORIZATION")
        identity, password = self._decode_baseauth(auth_header)
        # check if this is an email address or username
        user = self._user_manager.get_user_by_identity(identity)
        if not user:
            raise exceptions.ObjectNotFound("The user does not exist.")
        is_valid_user = self._auth_manager.check_password(user, password, request)
        if is_valid_user:
            key = self._api_keys_manager.get_or_create_api_key(user)
            return APIKeyResponse(api_key=key)
        else:
            raise exceptions.AuthenticationFailed("Invalid password.")

    def _decode_baseauth(self, encoded_str: Optional[Any]) -> Tuple[str, str]:
        """
        Decode an encrypted HTTP basic authentication string. Returns a tuple of
        the form (email, password), and raises a HTTPBadRequest exception if
        nothing could be decoded.

        :param  encoded_str: BaseAuth string encoded base64
        :type   encoded_str: string

        :returns: email of the user
        :rtype:   string
        :returns: password of the user
        :rtype:   string

        :raises: HTTPBadRequest
        """
        if encoded_str is None:
            raise exceptions.RequestParameterInvalidException("Authentication is missing")

        split = str(encoded_str).strip().split(" ")

        # If split is only one element, try to decode the email and password
        # directly.
        if len(split) == 1:
            try:
                email, password = unicodify(b64decode(smart_str(split[0]))).split(":")
            except Exception as e:
                raise exceptions.ActionInputError(e)

        # If there are only two elements, check the first and ensure it says
        # 'basic' so that we know we're about to decode the right thing. If not,
        # bail out.
        elif len(split) == 2:
            if split[0].strip().lower() == "basic":
                try:
                    email, password = unicodify(b64decode(smart_str(split[1]))).split(":")
                except Exception:
                    raise exceptions.ActionInputError("Invalid authorization line")
            else:
                raise exceptions.ActionInputError("Invalid authorization line")

        # If there are more than 2 elements, something crazy must be happening.
        # Bail.
        else:
            raise exceptions.ActionInputError("Invalid authorization line - more than two entries")

        return unquote(email), unquote(password)
