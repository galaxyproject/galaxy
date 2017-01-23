from contextlib import contextmanager

from six.moves.urllib.parse import urlencode

from .api_asserts import (
    assert_error_code_is,
    assert_has_keys,
    assert_not_has_keys,
    assert_status_code_is,
)
from .api_util import get_master_api_key, get_user_api_key
from .interactor import GalaxyInteractorApi as BaseInteractor
from .twilltestcase import FunctionalTestCase

TEST_USER = "user@bx.psu.edu"
DEFAULT_OTHER_USER = "otheruser@bx.psu.edu"  # A second user for API testing.


class UsesApiTestCaseMixin:

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

    def _setup_interactor( self ):
        self.user_api_key = get_user_api_key()
        self.master_api_key = get_master_api_key()
        self.galaxy_interactor = ApiTestInteractor( self )

    def _setup_user( self, email, password=None ):
        self.galaxy_interactor.ensure_user_with_email( email, password=password )
        users = self._get( "users", admin=True ).json()
        user = [ user for user in users if user["email"] == email ][0]
        return user

    def _setup_user_get_key( self, email ):
        self.galaxy_interactor.ensure_user_with_email( email )
        users = self._get( "users", admin=True ).json()
        user = [ user for user in users if user["email"] == email ][0]
        return self._post( "users/%s/api_key" % user[ "id" ], admin=True ).json()

    @contextmanager
    def _different_user( self, email=DEFAULT_OTHER_USER ):
        """ Use in test cases to switch get/post operations to act as new user,

            with self._different_user( "other_user@bx.psu.edu" ):
                self._get( "histories" )  # Gets other_user@bx.psu.edu histories.
        """
        original_api_key = self.user_api_key
        original_interactor_key = self.galaxy_interactor.api_key
        new_key = self._setup_user_get_key( email )
        try:
            self.user_api_key = new_key
            self.galaxy_interactor.api_key = new_key
            yield
        finally:
            self.user_api_key = original_api_key
            self.galaxy_interactor.api_key = original_interactor_key

    def _get( self, *args, **kwds ):
        return self.galaxy_interactor.get( *args, **kwds )

    def _post( self, *args, **kwds ):
        return self.galaxy_interactor.post( *args, **kwds )

    def _delete( self, *args, **kwds ):
        return self.galaxy_interactor.delete( *args, **kwds )

    def _patch( self, *args, **kwds ):
        return self.galaxy_interactor.patch( *args, **kwds )

    def _assert_status_code_is( self, response, expected_status_code ):
        assert_status_code_is( response, expected_status_code )

    def _assert_has_keys( self, response, *keys ):
        assert_has_keys( response, *keys )

    def _assert_not_has_keys( self, response, *keys ):
        assert_not_has_keys( response, *keys )

    def _assert_error_code_is( self, response, error_code ):
        assert_error_code_is( response, error_code )

    def _random_key( self ):  # Used for invalid request testing...
        return "1234567890123456"

    _assert_has_key = _assert_has_keys


class ApiTestCase(FunctionalTestCase, UsesApiTestCaseMixin):

    def setUp( self ):
        super( ApiTestCase, self ).setUp()
        self._setup_interactor()


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

    def delete( self, *args, **kwds ):
        return self._delete( *args, **kwds )

    def patch( self, *args, **kwds ):
        return self._patch( *args, **kwds )
