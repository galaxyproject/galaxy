import simplejson
from requests import post

from base import api
# from .helpers import DatasetPopulator

import logging
log = logging.getLogger( "functional_tests.py" )


class ApiBatchTestCase( api.ApiTestCase ):

    def _get_api_key( self, admin=False ):
        return self.galaxy_interactor.api_key if not admin else self.galaxy_interactor.master_api_key

    def _with_key( self, url, admin=False ):
        return url + '?key=' + self._get_api_key( admin=admin )

    def _post_batch( self, batch ):
        data = simplejson.dumps({ "batch" : batch })
        return post( "%s/batch" % ( self.galaxy_interactor.api_url ), data=data )

    def test_simple_array( self ):
        # post_body = dict( name='wert' )
        batch = [
            dict( url=self._with_key( '/api/histories' ) ),
            dict( url=self._with_key( '/api/histories' ),
                  method='POST', body=simplejson.dumps( dict( name='Wat' ) ) ),
            dict( url=self._with_key( '/api/histories' ) ),
        ]
        response = self._post_batch( batch )
        response = response.json()
        # log.debug( 'RESPONSE %s\n%s', ( '-' * 40 ), pprint.pformat( response ) )
        self.assertIsInstance( response, list )
        self.assertEquals( len( response ), 3 )
