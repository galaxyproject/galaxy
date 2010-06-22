import os, sys, urllib, urllib2

new_path = [ os.path.join( os.path.dirname( __file__ ), '..', '..', 'lib' ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
import pkg_resources

pkg_resources.require( "simplejson" )
import simplejson

def make_url( api_key, url, args=None ):
    # Adds the API Key to the URL if it's not already there.
    if args is None:
        args = []
    argsep = '&'
    if '?' not in url:
        argsep = '?'
    if '?key=' not in url and '&key=' not in url:
        args.insert( 0, ( 'key', api_key ) )
    return url + argsep + '&'.join( [ '='.join( t ) for t in args ] )

def get( api_key, url ):
    # Do the actual GET.
    url = make_url( api_key, url )
    return simplejson.loads( urllib2.urlopen( url ).read() )

def post( api_key, url, data ):
    # Do the actual POST.
    url = make_url( api_key, url )
    req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' }, data = simplejson.dumps( data ) )
    return simplejson.loads( urllib2.urlopen( req ).read() )

def display( api_key, url ):
    # Sends an API GET request and acts as a generic formatter for the JSON response.
    try:
        r = get( api_key, url )
    except urllib2.HTTPError, e:
        print e
        print e.read( 1024 ) # Only return the first 1K of errors.
        sys.exit( 1 )
    if type( r ) == unicode:
        print 'error: %s' % r
        return None
    elif type( r ) == list:
        # Response is a collection as defined in the REST style.
        print 'Collection Members'
        print '------------------'
        for i in r:
            # All collection members should have a name and url in the response.
            print i.pop( 'url' )
            print '  name: %s' % i.pop( 'name' )
            for k, v in i.items():
                print '  %s: %s' % ( k, v )
        print ''
        print '%d elements in collection' % len( r )
    elif type( r ) == dict:
        # Response is an element as defined in the REST style.
        print 'Member Information'
        print '------------------'
        for k, v in r.items():
            print '%s: %s' % ( k, v )
    else:
        print 'response is unknown type: %s' % type( r )

def submit( api_key, url, data ):
    # Sends an API POST request and acts as a generic formatter for the JSON response.
    # 'data' will become the JSON payload read by Galaxy.
    try:
        r = post( api_key, url, data )
    except urllib2.HTTPError, e:
        print e
        print e.read( 1024 )
        sys.exit( 1 )
    print 'Response'
    print '--------'
    if type( r ) == list:
        # Currently the only implemented responses are lists of dicts, because
        # submission creates some number of collection elements.
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
