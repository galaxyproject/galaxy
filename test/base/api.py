# TODO: We don't need all of TwillTestCase, strip down to a common super class
# shared by API and Twill test cases.
from .twilltestcase import TwillTestCase

from base.interactor import GalaxyInteractorApi as BaseInteractor

from .api_util import get_master_api_key
from .api_util import get_user_api_key

from urllib import urlencode


TEST_USER = "user@bx.psu.edu"


# TODO: Allow these to point at existing Galaxy instances.
class ApiTestCase( TwillTestCase ):

    def setUp( self ):
        super( ApiTestCase, self ).setUp( )
        self.user_api_key = get_user_api_key()
        self.master_api_key = get_master_api_key()
        self.galaxy_interactor = ApiTestInteractor( self )

    def _api_url( self, path, params=None, use_key=None ):
        if not params:
            params = {}
        url = "%s/api/%s" % ( self.url, path )
        if use_key:
            params[ "key" ] = self.galaxy_interactor.api_key
        query = urlencode( params )
        if query:
            url = "%s?%s" % ( url, query )
        return url

    def _setup_user( self, email ):
        self.galaxy_interactor.ensure_user_with_email(email)
        users = self._get( "users", admin=True ).json()
        user = [ user for user in users if user["email"] == email ][0]
        return user

    def _get( self, *args, **kwds ):
        return self.galaxy_interactor.get( *args, **kwds )

    def _post( self, *args, **kwds ):
        return self.galaxy_interactor.post( *args, **kwds )

    def _assert_status_code_is( self, response, expected_status_code ):
        response_status_code = response.status_code
        if expected_status_code != response_status_code:
            try:
                body = response.json()
            except Exception:
                body = "INVALID JSON RESPONSE"
            assertion_message_template = "Request status code (%d) was not expected value %d. Body was %s"
            assertion_message = assertion_message_template % ( response_status_code, expected_status_code, body )
            raise AssertionError( assertion_message )

    def _assert_has_keys( self, response, *keys ):
        for key in keys:
            assert key in response, "Response [%s] does not contain key [%s]" % ( response, key )

    def _random_key( self ):  # Used for invalid request testing...
        return "1234567890123456"

    _assert_has_key = _assert_has_keys


class ApiTestInteractor( BaseInteractor ):
    """ Specialized variant of the API interactor (originally developed for
    tool functional tests) for testing the API generally.
    """

    def __init__( self, test_case ):
        super( ApiTestInteractor, self ).__init__( test_case, test_user=TEST_USER )

    # This variant the lower level get and post methods are meant to be used
    # directly to test API - instead of relying on higher-level constructs for
    # specific pieces of the API (the way it is done with the variant for tool)
    # testing.
    def get( self, *args, **kwds ):
        return self._get( *args, **kwds )

    def post( self, *args, **kwds ):
        return self._post( *args, **kwds )
