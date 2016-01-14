"""
Unit tests for ``galaxy.web.framework.webapp``
"""
import os
import imp
import unittest

import logging
log = logging.getLogger( __name__ )

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '../../unittest_utils/utility.py' ) )
import galaxy_mock

import re
import tempfile
from galaxy.web.framework import webapp as Webapp
import galaxy.config


class StubGalaxyWebTransaction( Webapp.GalaxyWebTransaction ):
    def _ensure_valid_session( self, session_cookie, create=True ):
        pass


class GalaxyWebTransaction_Headers_TestCase( test_utils.unittest.TestCase ):

    def setUp( self ):
        # galaxy uses the tempfile.tempdir interface of the tempfile module, changing this value when a Configuration
        # is created. This change persists across tests (since it's scoped to the module) and breaks following tests.
        # TODO: most likely this should be changed at the core level to remove tempfile.tempdir - then remove this
        self._saved_tempfile_tempdir = tempfile.tempdir

    def teardown( self ):
        tempfile.tempdir = self._saved_tempfile_tempdir

    def _new_trans( self, allowed_origin_hostnames=None ):
        app = galaxy_mock.MockApp()
        app.config = galaxy.config.Configuration(
            allowed_origin_hostnames=allowed_origin_hostnames
        )
        webapp = galaxy_mock.MockWebapp()
        environ = galaxy_mock.buildMockEnviron()
        trans = StubGalaxyWebTransaction( environ, app, webapp )
        return trans

    def assert_cors_header_equals( self, headers, should_be ):
        self.assertEqual( headers[ 'access-control-allow-origin' ], should_be )

    def assert_cors_header_missing( self, headers ):
        self.assertFalse( 'access-control-allow-origin' in headers )

    def test_default_allowed_origin_hostnames( self ):
        """Shouldn't have any allowed"""
        config = galaxy.config.Configuration()
        self.assertTrue( isinstance( config, galaxy.config.Configuration ) )
        self.assertEqual( config.allowed_origin_hostnames, None )

    def test_parse_allowed_origin_hostnames( self ):
        """Should return a list of (possibly) mixed strings and regexps"""
        config = galaxy.config.Configuration()

        # falsy listify value should return None
        self.assertEqual( config._parse_allowed_origin_hostnames({
            "allowed_origin_hostnames" : ""
        }), None )

        # should parse regex if using fwd slashes, string otherwise
        hostnames = config._parse_allowed_origin_hostnames({
            "allowed_origin_hostnames" : "/host\d{2}/,geocities.com,miskatonic.edu"
        })
        self.assertTrue( isinstance( hostnames[0], re._pattern_type ) )
        self.assertTrue( isinstance( hostnames[1], str ) )
        self.assertTrue( isinstance( hostnames[2], str ) )

    def test_default_set_cors_headers( self ):
        """No CORS headers should be set (or even checked) by default"""
        trans = self._new_trans( allowed_origin_hostnames=None )
        self.assertTrue( isinstance( trans, Webapp.GalaxyWebTransaction ) )

        trans.request.headers[ 'Origin' ] = 'http://lisaskelprecipes.pinterest.com?id=kelpcake'
        trans.set_cors_headers()
        self.assert_cors_header_missing( trans.response.headers )

    def test_set_cors_headers( self ):
        """Origin should be echo'd when it matches an allowed hostname"""
        # an asterisk is a special 'allow all' string
        trans = self._new_trans( allowed_origin_hostnames='*,beep.com' )
        trans.request.headers[ 'Origin' ] = 'http://xxdarkhackerxx.disney.com'
        trans.set_cors_headers()
        self.assert_cors_header_equals( trans.response.headers, 'http://xxdarkhackerxx.disney.com' )

        # subdomains should pass
        trans = self._new_trans( allowed_origin_hostnames='something.com,/^[\w\.]*beep\.com/' )
        trans.request.headers[ 'Origin' ] = 'http://boop.beep.com'
        trans.set_cors_headers()
        self.assert_cors_header_equals( trans.response.headers, 'http://boop.beep.com' )

        # ports should work
        trans = self._new_trans( allowed_origin_hostnames='somethingelse.com,/^[\w\.]*beep\.com/' )
        trans.request.headers[ 'Origin' ] = 'http://boop.beep.com:8080'
        trans.set_cors_headers()
        self.assert_cors_header_equals( trans.response.headers, 'http://boop.beep.com:8080' )

        # localhost should work
        trans = self._new_trans( allowed_origin_hostnames='/localhost/' )
        trans.request.headers[ 'Origin' ] = 'http://localhost:8080'
        trans.set_cors_headers()
        self.assert_cors_header_equals( trans.response.headers, 'http://localhost:8080' )

        # spoofing shouldn't be easy
        trans.response.headers = {}
        trans.request.headers[ 'Origin' ] = 'http://localhost.badstuff.tv'
        trans.set_cors_headers()
        self.assert_cors_header_missing( trans.response.headers )

        # unicode should work
        trans = self._new_trans( allowed_origin_hostnames='/öbb\.at/' )
        trans.request.headers[ 'Origin' ] = 'http://öbb.at'
        trans.set_cors_headers()
        self.assertEqual(
            trans.response.headers[ 'access-control-allow-origin' ], 'http://öbb.at'
        )


if __name__ == '__main__':
    unittest.main()
