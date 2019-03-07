"""
API key retrieval through BaseAuth
Sample usage:

curl --user zipzap@foo.com:password http://localhost:8080/api/authenticate/baseauth

Returns:

{
    "api_key": "baa4d6e3a156d3033f05736255f195f9"
}
"""
import logging
from base64 import b64decode

from six.moves.urllib.parse import unquote

from galaxy import exceptions
from galaxy.managers import api_keys
from galaxy.util import (
    smart_str,
    unicodify
)
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class AuthenticationController(BaseAPIController):

    def __init__(self, app):
        super(AuthenticationController, self).__init__(app)
        self.api_keys_manager = api_keys.ApiKeyManager(app)

    @expose_api_anonymous_and_sessionless
    def get_api_key(self, trans, **kwd):
        """
        def get_api_key( self, trans, **kwd )
        * GET /api/authenticate/baseauth
          returns an API key for authenticated user based on BaseAuth headers

        :returns: api_key in json format
        :rtype:   dict

        :raises: ObjectNotFound, HTTPBadRequest
        """
        email, password = self._decode_baseauth(trans.environ.get('HTTP_AUTHORIZATION'))

        user = trans.sa_session.query(trans.app.model.User).filter(trans.app.model.User.table.c.email == email).all()

        if len(user) == 0:
            raise exceptions.ObjectNotFound('The user does not exist.')
        elif len(user) > 1:
            # DB is inconsistent and we have more users with the same email.
            raise exceptions.InconsistentDatabase('An error occurred, please contact your administrator.')
        else:
            user = user[0]
            is_valid_user = self.app.auth_manager.check_password(user, password)
        if is_valid_user:
            key = self.api_keys_manager.get_or_create_api_key(user)
            return dict(api_key=key)
        else:
            raise exceptions.AuthenticationFailed('Invalid password.')

    def _decode_baseauth(self, encoded_str):
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
        split = encoded_str.strip().split(' ')

        # If split is only one element, try to decode the email and password
        # directly.
        if len(split) == 1:
            try:
                email, password = unicodify(b64decode(smart_str(split[0]))).split(':')
            except Exception as e:
                raise exceptions.ActionInputError(str(e))

        # If there are only two elements, check the first and ensure it says
        # 'basic' so that we know we're about to decode the right thing. If not,
        # bail out.
        elif len(split) == 2:
            if split[0].strip().lower() == 'basic':
                try:
                    email, password = unicodify(b64decode(smart_str(split[1]))).split(':')
                except Exception:
                    raise exceptions.ActionInputError()
            else:
                raise exceptions.ActionInputError()

        # If there are more than 2 elements, something crazy must be happening.
        # Bail.
        else:
            raise exceptions.ActionInputError()

        return unquote(email), unquote(password)
