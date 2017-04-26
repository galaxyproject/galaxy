#!/usr/bin/env python
# Dan Blankenberg
from __future__ import print_function

import base64
import binascii
import datetime
import hashlib
import json
import logging
import optparse
import os
import tempfile

import six
from six.moves import http_cookiejar
from six.moves.urllib.error import HTTPError
from six.moves.urllib.parse import quote, urlencode, urljoin
from six.moves.urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen

log = logging.getLogger( "tools.genomespace.genomespace_exporter" )

try:
    import boto
    from boto.s3.connection import S3Connection
except ImportError:
    boto = None

GENOMESPACE_API_VERSION_STRING = "v1.0"
GENOMESPACE_SERVER_URL_PROPERTIES = "https://dm.genomespace.org/config/%s/serverurl.properties" % ( GENOMESPACE_API_VERSION_STRING )
DEFAULT_GENOMESPACE_TOOLNAME = 'Galaxy'

CHUNK_SIZE = 2 ** 20  # 1mb

# TODO: TARGET_SPLIT_SIZE and TARGET_SIMPLE_PUT_UPLOAD_SIZE are arbitrarily defined
# we should programmatically determine these, based upon the current environment
TARGET_SPLIT_SIZE = 250 * 1024 * 1024  # 250 mb
MIN_MULTIPART_UPLOAD_SIZE = 5 * 1024 * 1024  # 5mb
MAX_SIMPLE_PUT_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024  # 5gb
TARGET_SIMPLE_PUT_UPLOAD_SIZE = MAX_SIMPLE_PUT_UPLOAD_SIZE / 2

# Some basic Caching, so we don't have to reload and download everything every time,
# especially now that we are calling the parameter's get options method 5 times
# (6 on reload) when a user loads the tool interface
# For now, we'll use 30 seconds as the cache valid time
CACHE_TIME = datetime.timedelta( seconds=30 )
GENOMESPACE_DIRECTORIES_BY_USER = {}


def chunk_write( source_stream, target_stream, source_method="read", target_method="write" ):
    source_method = getattr( source_stream, source_method )
    target_method = getattr( target_stream, target_method )
    while True:
        chunk = source_method( CHUNK_SIZE )
        if chunk:
            target_method( chunk )
        else:
            break


def get_cookie_opener( gs_username, gs_token, gs_toolname=None ):
    """ Create a GenomeSpace cookie opener """
    cj = http_cookiejar.CookieJar()
    for cookie_name, cookie_value in [ ( 'gs-token', gs_token ), ( 'gs-username', gs_username ) ]:
        # create a super-cookie, valid for all domains
        cookie = http_cookiejar.Cookie(version=0, name=cookie_name, value=cookie_value, port=None, port_specified=False, domain='', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False )
        cj.set_cookie( cookie )
    cookie_opener = build_opener( HTTPCookieProcessor( cj ) )
    cookie_opener.addheaders.append( ( 'gs-toolname', gs_toolname or DEFAULT_GENOMESPACE_TOOLNAME ) )
    return cookie_opener


def get_genomespace_site_urls():
    genomespace_sites = {}
    for line in urlopen( GENOMESPACE_SERVER_URL_PROPERTIES ).read().split( '\n' ):
        line = line.rstrip()
        if not line or line.startswith( "#" ):
            continue
        server, line = line.split( '.', 1 )
        if server not in genomespace_sites:
            genomespace_sites[server] = {}
        line = line.split( "=", 1 )
        genomespace_sites[server][line[0]] = line[1]
    return genomespace_sites


def get_directory( url_opener, dm_url, path ):
    url = dm_url
    i = None
    dir_dict = {}
    for i, sub_path in enumerate( path ):
        url = "%s/%s" % ( url, sub_path )
        dir_request = Request( url, headers={ 'Content-Type': 'application/json', 'Accept': 'application/json' } )
        dir_request.get_method = lambda: 'GET'
        try:
            dir_dict = json.loads( url_opener.open( dir_request ).read() )
        except HTTPError:
            # print "e", e, url #punting, assuming lack of permissions at this low of a level...
            continue
        break
    if i is not None:
        path = path[i + 1:]
    else:
        path = []
    return ( dir_dict, path )


def get_default_directory( url_opener, dm_url ):
    return get_directory( url_opener, dm_url, ["%s/defaultdirectory" % ( GENOMESPACE_API_VERSION_STRING ) ] )[0]


def get_personal_directory( url_opener, dm_url ):
    return get_directory( url_opener, dm_url, [ "%s/personaldirectory" % ( GENOMESPACE_API_VERSION_STRING ) ] )[0]


def create_directory( url_opener, directory_dict, new_dir, dm_url ):
    payload = { "isDirectory": True }
    for dir_slice in new_dir:
        if dir_slice in ( '', '/', None ):
            continue
        url = '/'.join( ( directory_dict['url'], quote( dir_slice.replace( '/', '_' ), safe='' ) ) )
        new_dir_request = Request( url, headers={ 'Content-Type': 'application/json', 'Accept': 'application/json' }, data=json.dumps( payload ) )
        new_dir_request.get_method = lambda: 'PUT'
        directory_dict = json.loads( url_opener.open( new_dir_request ).read() )
    return directory_dict


def get_genome_space_launch_apps( atm_url, url_opener, file_url, file_type ):
    gs_request = Request( "%s/%s/webtool/descriptor" % ( atm_url, GENOMESPACE_API_VERSION_STRING ) )
    gs_request.get_method = lambda: 'GET'
    opened_gs_request = url_opener.open( gs_request )
    webtool_descriptors = json.loads( opened_gs_request.read() )
    webtools = []
    for webtool in webtool_descriptors:
        webtool_name = webtool.get( 'name' )
        base_url = webtool.get( 'baseUrl' )
        use_tool = False
        for param in webtool.get( 'fileParameters', [] ):
            for format in param.get( 'formats', [] ):
                if format.get( 'name' ) == file_type:
                    use_tool = True
                    break
            if use_tool:
                file_param_name = param.get( 'name' )
                # file_name_delimiters = param.get( 'nameDelimiters' )
                if '?' in base_url:
                    url_delimiter = "&"
                else:
                    url_delimiter = "?"
                launch_url = "%s%s%s" % ( base_url, url_delimiter, urlencode( [ ( file_param_name, file_url ) ] ) )
                webtools.append( ( launch_url, webtool_name ) )
                break
    return webtools


def galaxy_code_get_genomespace_folders( genomespace_site='prod', trans=None, value=None, base_url=None, **kwd ):
    if value:
        if isinstance( value, list ):
            value = value[0]  # single select, only 1 value
        elif not isinstance( value, six.string_types ):
            # unvalidated value
            value = value.value
            if isinstance( value, list ):
                value = value[0]  # single select, only 1 value

    def recurse_directory_dict( url_opener, cur_options, url ):
        cur_directory = Request( url, headers={ 'Content-Type': 'application/json', 'Accept': 'application/json, text/plain' } )
        cur_directory.get_method = lambda: 'GET'
        # get url to upload to
        try:
            cur_directory = url_opener.open( cur_directory ).read()
        except HTTPError as e:
            log.debug( 'GenomeSpace export tool failed reading a directory "%s": %s' % ( url, e ) )
            return  # bad url, go to next
        cur_directory = json.loads( cur_directory )
        directory = cur_directory.get( 'directory', {} )
        contents = cur_directory.get( 'contents', [] )
        if directory.get( 'isDirectory', False ):
            selected = directory.get( 'path' ) == value
            cur_options.append( { 'name': directory.get( 'name' ), 'value': directory.get( 'path'), 'options': [], 'selected': selected  } )
            for sub_dir in contents:
                if sub_dir.get( 'isDirectory', False ):
                    recurse_directory_dict( url_opener, cur_options[-1]['options'], sub_dir.get( 'url' ) )

    rval = []
    if trans and trans.user:
        username = trans.user.preferences.get( 'genomespace_username', None )
        token = trans.user.preferences.get( 'genomespace_token', None )
        if None not in ( username, token ):
            # NB: it is possible, but unlikely for a user to swap GenomeSpace accounts around
            # in the middle of interacting with tools, so we'll have several layers of caching by ids/values
            if trans.user in GENOMESPACE_DIRECTORIES_BY_USER:
                if username in GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ]:
                    if token in GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ][ username ]:
                        cache_dict = GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ][ username ][ token ]
                        if datetime.datetime.now() - cache_dict.get( 'time_loaded' ) > CACHE_TIME:
                            # cache too old, need to reload, we'll just kill the whole trans.user
                            del GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ]
                        else:
                            rval = cache_dict.get( 'rval' )
                    else:
                        del GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ]
                else:
                    del GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ]
            if not rval:
                url_opener = get_cookie_opener( username, token, gs_toolname=os.environ.get( 'GENOMESPACE_TOOLNAME', None ) )
                genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
                dm_url = genomespace_site_dict['dmServer']
                # get export root directory
                # directory_dict = get_default_directory( url_opener, dm_url ).get( 'directory', None ) #This directory contains shares and other items outside of the users home
                directory_dict = get_personal_directory( url_opener, dm_url ).get( 'directory', None )  # Limit export list to only user's home dir
                if directory_dict is not None:
                    recurse_directory_dict( url_opener, rval, directory_dict.get( 'url' ) )
                # Save the cache
                GENOMESPACE_DIRECTORIES_BY_USER[ trans.user ] = { username: { token: { 'time_loaded': datetime.datetime.now(), 'rval': rval } }  }
    if not rval:
        if not base_url:
            base_url = '..'
        rval = [ { 'name': 'Your GenomeSpace token appears to be <strong>expired</strong>, please <a href="%s">reauthenticate</a>.' % ( urljoin( base_url, 'user/openid_auth?openid_provider=genomespace&amp;auto_associate=True' ) ), 'value': '', 'options': [], 'selected': False  } ]
    return rval


def send_file_to_genomespace( genomespace_site, username, token, source_filename, target_directory, target_filename, file_type, content_type, log_filename, gs_toolname ):
    target_filename = target_filename.replace( '/', '-' )  # Slashes no longer allowed in filenames
    url_opener = get_cookie_opener( username, token, gs_toolname=gs_toolname )
    genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
    dm_url = genomespace_site_dict['dmServer']
    # get default directory
    if target_directory and target_directory[0] == '/':
        directory_dict, target_directory = get_directory( url_opener, dm_url, [ "%s/%s/%s" % ( GENOMESPACE_API_VERSION_STRING, 'file', target_directory[1] ) ] + target_directory[2:] )
        directory_dict = directory_dict['directory']
    else:
        directory_dict = get_personal_directory( url_opener, dm_url )['directory']  # this is the base for the auto-generated galaxy export directories
    # what directory to stuff this in
    target_directory_dict = create_directory( url_opener, directory_dict, target_directory, dm_url )
    content_length = os.path.getsize( source_filename )
    input_file = open( source_filename, 'rb' )
    if content_length > TARGET_SIMPLE_PUT_UPLOAD_SIZE:
        # Determine sizes of each part.
        split_count = content_length / TARGET_SPLIT_SIZE
        last_size = content_length - ( split_count * TARGET_SPLIT_SIZE )
        sizes = [ TARGET_SPLIT_SIZE ] * split_count
        if last_size:
            if last_size < MIN_MULTIPART_UPLOAD_SIZE:
                if sizes:
                    sizes[-1] = sizes[-1] + last_size
                else:
                    sizes = [ last_size ]
            else:
                sizes.append( last_size )
        print("Performing multi-part upload in %i parts." % ( len( sizes ) ))
        # get upload url
        upload_url = "uploadinfo"
        upload_url = "%s/%s/%s%s/%s" % ( dm_url, GENOMESPACE_API_VERSION_STRING, upload_url, target_directory_dict['path'], quote( target_filename, safe='' ) )
        upload_request = Request( upload_url, headers={ 'Content-Type': 'application/json', 'Accept': 'application/json' } )
        upload_request.get_method = lambda: 'GET'
        upload_info = json.loads( url_opener.open( upload_request ).read() )
        conn = S3Connection( aws_access_key_id=upload_info['amazonCredentials']['accessKey'],
                             aws_secret_access_key=upload_info['amazonCredentials']['secretKey'],
                             security_token=upload_info['amazonCredentials']['sessionToken'] )
        # Cannot use conn.get_bucket due to permissions, manually create bucket object
        bucket = boto.s3.bucket.Bucket( connection=conn, name=upload_info['s3BucketName'] )
        mp = bucket.initiate_multipart_upload( upload_info['s3ObjectKey'] )
        for i, part_size in enumerate( sizes, start=1 ):
            fh = tempfile.TemporaryFile( 'wb+' )
            while part_size:
                if CHUNK_SIZE > part_size:
                    read_size = part_size
                else:
                    read_size = CHUNK_SIZE
                chunk = input_file.read( read_size )
                fh.write( chunk )
                part_size = part_size - read_size
            fh.flush()
            fh.seek(0)
            mp.upload_part_from_file( fh, i )
            fh.close()
        upload_result = mp.complete_upload()
    else:
        print('Performing simple put upload.')
        upload_url = "uploadurl"
        content_md5 = hashlib.md5()
        chunk_write( input_file, content_md5, target_method="update" )
        input_file.seek( 0 )  # back to start, for uploading

        upload_params = { 'Content-Length': content_length, 'Content-MD5': base64.standard_b64encode( content_md5.digest() ), 'Content-Type': content_type }
        upload_url = "%s/%s/%s%s/%s?%s" % ( dm_url, GENOMESPACE_API_VERSION_STRING, upload_url, target_directory_dict['path'], quote( target_filename, safe='' ), urlencode( upload_params ) )
        new_file_request = Request( upload_url )  # , headers = { 'Content-Type': 'application/json', 'Accept': 'application/text' } ) #apparently http://www.genomespace.org/team/specs/updated-dm-rest-api:"Every HTTP request to the Data Manager should include the Accept header with a preference for the media types application/json and application/text." is not correct
        new_file_request.get_method = lambda: 'GET'
        # get url to upload to
        target_upload_url = url_opener.open( new_file_request ).read()
        # upload file to determined url
        upload_headers = dict( upload_params )
        # upload_headers[ 'x-amz-meta-md5-hash' ] = content_md5.hexdigest()
        upload_headers[ 'Accept' ] = 'application/json'
        upload_file_request = Request( target_upload_url, headers=upload_headers, data=input_file )
        upload_file_request.get_method = lambda: 'PUT'
        upload_result = urlopen( upload_file_request ).read()
    result_url = "%s/%s" % ( target_directory_dict['url'], quote( target_filename, safe='' ) )
    # determine available gs launch apps
    web_tools = get_genome_space_launch_apps( genomespace_site_dict['atmServer'], url_opener, result_url, file_type )
    if log_filename:
        log_file = open( log_filename, 'wb' )
        log_file.write( "<html><head><title>File uploaded to GenomeSpace from Galaxy</title></head><body>\n" )
        log_file.write( '<p>Uploaded <a href="%s">%s/%s</a> to GenomeSpace.</p>\n' % ( result_url, target_directory_dict['path'], target_filename ) )
        if web_tools:
            log_file.write( "<p>You may open this file directly in the following applications:</p>\n" )
            log_file.write( '<p><ul>\n' )
            for web_tool in web_tools:
                log_file.write( '<li><a href="%s">%s</a></li>\n' % ( web_tool ) )
            log_file.write( '</p></ul>\n' )
        else:
            log_file.write( '<p>There are no GenomeSpace applications available for file type: %s</p>\n' % ( file_type ) )
        log_file.write( "</body></html>\n" )
    return upload_result


if __name__ == '__main__':
    # Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-s', '--genomespace_site', dest='genomespace_site', action='store', type="string", default=None, help='genomespace_site' )
    parser.add_option( '-t', '--token', dest='token', action='store', type="string", default=None, help='token' )
    parser.add_option( '-u', '--username', dest='username', action='store', type="string", default=None, help='username' )
    parser.add_option( '-d', '--dataset', dest='dataset', action='store', type="string", default=None, help='dataset' )
    parser.add_option( '-f', '--filename', dest='filename', action='store', type="string", default=None, help='filename' )
    parser.add_option( '-y', '--subdirectory', dest='subdirectory', action='append', type="string", default=None, help='subdirectory' )
    parser.add_option( '', '--file_type', dest='file_type', action='store', type="string", default=None, help='file_type' )
    parser.add_option( '-c', '--content_type', dest='content_type', action='store', type="string", default=None, help='content_type' )
    parser.add_option( '-l', '--log', dest='log', action='store', type="string", default=None, help='log' )
    parser.add_option( '', '--genomespace_toolname', dest='genomespace_toolname', action='store', type="string", default=DEFAULT_GENOMESPACE_TOOLNAME, help='value to use for gs-toolname, used in GenomeSpace internal logging' )

    (options, args) = parser.parse_args()

    send_file_to_genomespace( options.genomespace_site, options.username, options.token, options.dataset, [binascii.unhexlify(_) for _ in options.subdirectory], binascii.unhexlify( options.filename ), options.file_type, options.content_type, options.log, options.genomespace_toolname )
