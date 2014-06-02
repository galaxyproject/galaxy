import json
import os
import sys
import urllib
import urllib2

new_path = [ os.path.join( os.path.dirname( __file__ ), '..', '..', '..', '..', 'lib' ) ]
new_path.extend( sys.path[ 1: ] )
sys.path = new_path

import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util

from galaxy import eggs
import pkg_resources

def delete( api_key, url, data, return_formatted=True ):
    """
    Sends an API DELETE request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        url = make_url( url, api_key=api_key, args=None )
        req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = json.dumps( data ))
        req.get_method = lambda: 'DELETE'
        r = json.loads( urllib2.urlopen( req ).read() )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. '+ str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    print r

def display( url, api_key=None, return_formatted=True ):
    """Sends an API GET request and acts as a generic formatter for the JSON response."""
    try:
        r = get( url, api_key=api_key )
    except urllib2.HTTPError, e:
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
            # All collection members should have a name and url in the response.
            print '#%d: %s' % (n+1, i.pop( 'url' ) )
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
    except ValueError, e:
        print "URL did not return JSON data"
        sys.exit( 1 )

def get_api_url( base, parts=[], params=None ):
    """Compose and return a URL for the Tool Shed API."""
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts:
        parts.insert( 0, 'api' )
    url = common_util.url_join( base, *parts )
    if params is not None:
        try:
            query_string = urllib.urlencode( params )
        except Exception, e:
            # The value of params must be a string.
            query_string = params
        url += '?%s' % query_string
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
    return suc.INITIAL_CHANGELOG_HASH, error_message

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
    except Exception, e:
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
    url = make_url( url, api_key=api_key, args=None )
    req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = json.dumps( data ) )
    return json.loads( urllib2.urlopen( req ).read() )

def put( url, data, api_key=None ):
    """Do the PUT."""
    url = make_url( url, api_key=api_key, args=None )
    req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = json.dumps( data ))
    req.get_method = lambda: 'PUT'
    return json.loads( urllib2.urlopen( req ).read() )

def submit( url, data, api_key=None, return_formatted=True ):
    """
    Sends an API POST request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        r = post( url, data, api_key=api_key )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. '+ str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    if type( r ) == list:
        # Currently the only implemented responses are lists of dicts, because submission creates
        # some number of collection elements.
        for i in r:
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
        print r

def update( api_key, url, data, return_formatted=True ):
    """
    Sends an API PUT request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    try:
        r = put( url, data, api_key=api_key )
    except urllib2.HTTPError, e:
        if return_formatted:
            print e
            print e.read( 1024 )
            sys.exit( 1 )
        else:
            return 'Error. ' + str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print 'Response'
    print '--------'
    print r
