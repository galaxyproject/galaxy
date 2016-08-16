import json
import os
import sys
import urllib
import urllib2

sys.path.insert( 1, os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir, os.pardir, 'lib' ) )

from galaxy import util
from tool_shed.util import hg_util


class HTTPRedirectWithDataHandler( urllib2.HTTPRedirectHandler ):

    def __init__( self, method ):
        '''
        Upon first inspection, it would seem that this shouldn't be necessary, but for some reason
        not having a constructor explicitly set the request method breaks PUT requests.
        '''
        self.valid_methods = [ 'GET', 'HEAD', 'POST', 'PUT', 'DELETE' ]
        self.redirect_codes = [ '301', '302', '303', '307' ]
        self.method = method

    def redirect_request( self, request, fp, code, msg, headers, new_url ):
        request_method = request.get_method()
        if str( code ) in self.redirect_codes and request_method in self.valid_methods:
            new_url = new_url.replace( ' ', '%20' )
            request = urllib2.Request( new_url,
                                       data=request.data,
                                       headers=request.headers,
                                       origin_req_host=request.get_origin_req_host(),
                                       unverifiable=True )
            if self.method in self.valid_methods:
                if request.get_method() != self.method:
                    request.get_method = lambda: self.method
            return request
        else:
            urllib2.HTTPRedirectHandler.redirect_request( request, fp, code, msg, headers, new_url )


def build_request_with_data( url, data, api_key, method ):
    """Build a request with the received method."""
    http_redirect_with_data_handler = HTTPRedirectWithDataHandler( method=method )
    opener = urllib2.build_opener( http_redirect_with_data_handler )
    urllib2.install_opener( opener )
    url = make_url( url, api_key=api_key, args=None )
    request = urllib2.Request( url, headers={ 'Content-Type': 'application/json' }, data=json.dumps( data ) )
    request_method = request.get_method()
    if request_method != method:
        request.get_method = lambda: method
    return opener, request


def delete( api_key, url, data, return_formatted=True ):
    """
    Sends an API DELETE request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        opener, request = build_request_with_data( url, data, api_key, 'DELETE' )
        delete_request = opener.open( request )
        response = json.loads( delete_request.read() )
    except urllib2.HTTPError as e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return dict( status='error', message=str( e.read( 1024 ) ) )
    if return_formatted:
        print 'Response'
        print '--------'
        print response
    else:
        return response


def display( url, api_key=None, return_formatted=True ):
    """Sends an API GET request and acts as a generic formatter for the JSON response."""
    try:
        r = get( url, api_key=api_key )
    except urllib2.HTTPError as e:
        print e
        # Only return the first 1K of errors.
        print e.read( 1024 )
        sys.exit( 1 )
    if type( r ) == unicode:
        print 'error: %s' % r
        return None
    if not return_formatted:
        return r
    elif type( r ) == list:
        # Response is a collection as defined in the REST style.
        print 'Collection Members'
        print '------------------'
        for n, i in enumerate(r):
            # All collection members should have a name in the response.
            # url is optional
            if 'url' in i:
                print '#%d: %s' % (n + 1, i.pop( 'url' ) )
            if 'name' in i:
                print '  name: %s' % i.pop( 'name' )
            for k, v in i.items():
                print '  %s: %s' % ( k, v )
        print ''
        print '%d element(s) in collection' % len( r )
    elif type( r ) == dict:
        # Response is an element as defined in the REST style.
        print 'Member Information'
        print '------------------'
        for k, v in r.items():
            print '%s: %s' % ( k, v )
    elif type( r ) == str:
        print r
    else:
        print 'response is unknown type: %s' % type( r )


def get( url, api_key=None ):
    """Do the GET."""
    url = make_url( url, api_key=api_key, args=None )
    try:
        return json.loads( urllib2.urlopen( url ).read() )
    except ValueError:
        sys.exit( "URL did not return JSON data" )


def get_api_url( base, parts=[], params=None ):
    """Compose and return a URL for the Tool Shed API."""
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts:
        parts.insert( 0, 'api' )
    url = util.build_url( base, pathspec=parts, params=params )
    return url


def get_latest_downloadable_changeset_revision_via_api( url, name, owner ):
    """
    Return the latest downloadable changeset revision for the repository defined by the received
    name and owner.
    """
    error_message = ''
    parts = [ 'api', 'repositories', 'get_ordered_installable_revisions' ]
    params = dict( name=name, owner=owner )
    api_url = get_api_url( base=url, parts=parts, params=params )
    changeset_revisions, error_message = json_from_url( api_url )
    if changeset_revisions is None or error_message:
        return None, error_message
    if len( changeset_revisions ) >= 1:
        return changeset_revisions[ -1 ], error_message
    return hg_util.INITIAL_CHANGELOG_HASH, error_message


def get_repository_dict( url, repository_dict ):
    """
    Send a request to the Tool Shed to get additional information about the repository defined
    by the received repository_dict.  Add the information to the repository_dict and return it.
    """
    error_message = ''
    if not isinstance( repository_dict, dict ):
        error_message = 'Invalid repository_dict received: %s' % str( repository_dict )
        return None, error_message
    repository_id = repository_dict.get( 'repository_id', None )
    if repository_id is None:
        error_message = 'Invalid repository_dict does not contain a repository_id entry: %s' % str( repository_dict )
        return None, error_message
    parts = [ 'api', 'repositories', repository_id ]
    api_url = get_api_url( base=url, parts=parts )
    extended_dict, error_message = json_from_url( api_url )
    if extended_dict is None or error_message:
        return None, error_message
    name = extended_dict.get( 'name', None )
    owner = extended_dict.get( 'owner', None )
    if name is not None and owner is not None:
        name = str( name )
        owner = str( owner )
        latest_changeset_revision, error_message = get_latest_downloadable_changeset_revision_via_api( url, name, owner )
        if latest_changeset_revision is None or error_message:
            return None, error_message
        extended_dict[ 'latest_revision' ] = str( latest_changeset_revision )
        return extended_dict, error_message
    else:
        error_message = 'Invalid extended_dict does not contain name or owner entries: %s' % str( extended_dict )
        return None, error_message


def json_from_url( url ):
    """Send a request to the Tool Shed via the Tool Shed API and handle the response."""
    error_message = ''
    url_handle = urllib.urlopen( url )
    url_contents = url_handle.read()
    try:
        parsed_json = json.loads( url_contents )
    except Exception as e:
        error_message = str( url_contents )
        print 'Error parsing JSON data in json_from_url(): ', str( e )
        return None, error_message
    return parsed_json, error_message


def make_url( url, api_key=None, args=None ):
    """Adds the API Key to the URL if it's not already there."""
    if args is None:
        args = []
    argsep = '&'
    if '?' not in url:
        argsep = '?'
    if api_key:
        if '?key=' not in url and '&key=' not in url:
            args.insert( 0, ( 'key', api_key ) )
    return url + argsep + '&'.join( [ '='.join( t ) for t in args ] )


def post( url, data, api_key=None ):
    """Do the POST."""
    try:
        opener, request = build_request_with_data( url, data, api_key, 'POST' )
        post_request = opener.open( request )
        return json.loads( post_request.read() )
    except urllib2.HTTPError as e:
        return dict( status='error', message=str( e.read( 1024 ) ) )


def put( url, data, api_key=None ):
    """Do the PUT."""
    try:
        opener, request = build_request_with_data( url, data, api_key, 'PUT' )
        put_request = opener.open( request )
        return json.loads( put_request.read() )
    except urllib2.HTTPError as e:
        return dict( status='error', message=str( e.read( 1024 ) ) )


def submit( url, data, api_key=None, return_formatted=True ):
    """
    Sends an API POST request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        response = post( url, data, api_key=api_key )
    except urllib2.HTTPError as e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return dict( status='error', message=str( e.read( 1024 ) ) )
    if not return_formatted:
        return response
    print 'Response'
    print '--------'
    if type( response ) == list:
        # Currently the only implemented responses are lists of dicts, because submission creates
        # some number of collection elements.
        for i in response:
            if type( i ) == dict:
                if 'url' in i:
                    print i.pop( 'url' )
                else:
                    print '----'
                if 'name' in i:
                    print '  name: %s' % i.pop( 'name' )
                for k, v in i.items():
                    print '  %s: %s' % ( k, v )
            else:
                print i
    else:
        print response


def update( api_key, url, data, return_formatted=True ):
    """
    Sends an API PUT request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        response = put( url, data, api_key=api_key )
    except urllib2.HTTPError as e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return dict( status='error', message=str( e.read( 1024 ) ) )
    if return_formatted:
        print 'Response'
        print '--------'
        print response
    else:
        return response
