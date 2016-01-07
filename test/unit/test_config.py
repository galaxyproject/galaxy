"""
Unit tests for ``galaxy.config``
"""
import os
import imp
import unittest

import logging
log = logging.getLogger( __name__ )

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), './unittest_utils/utility.py' ) )
# import galaxy_mock
import re
import galaxy.config


class Config_TestCase( test_utils.unittest.TestCase ):

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


if __name__ == '__main__':
    unittest.main()
