#Dan Blankenberg

import optparse, os, urllib2, urllib, cookielib, hashlib, base64, cgi, binascii

from galaxy import eggs
import pkg_resources

pkg_resources.require( "simplejson" )
import simplejson

GENOMESPACE_API_VERSION_STRING = "v1.0"
GENOMESPACE_SERVER_URL_PROPERTIES = "http://www.genomespace.org/sites/genomespacefiles/config/serverurl.properties"

CHUNK_SIZE = 2**20 #1mb


def chunk_write( source_stream, target_stream, source_method = "read", target_method="write" ):
    source_method = getattr( source_stream, source_method )
    target_method = getattr( target_stream, target_method )
    while True:
        chunk = source_method( CHUNK_SIZE )
        if chunk:
            target_method( chunk )
        else:
            break

def get_cookie_opener( gs_username, gs_token ):
    """ Create a GenomeSpace cookie opener """
    cj = cookielib.CookieJar()
    for cookie_name, cookie_value in [ ( 'gs-token', gs_token ), ( 'gs-username', gs_username ) ]:
        #create a super-cookie, valid for all domains
        cookie = cookielib.Cookie(version=0, name=cookie_name, value=cookie_value, port=None, port_specified=False, domain='', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False )
        cj.set_cookie( cookie )
    cookie_opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( cj ) )
    return cookie_opener

def get_genomespace_site_urls():
    genomespace_sites = {}
    for line in urllib2.urlopen( GENOMESPACE_SERVER_URL_PROPERTIES ).read().split( '\n' ):
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
        dir_request = urllib2.Request( url, headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' } )
        dir_request.get_method = lambda: 'GET'
        try:
            dir_dict = simplejson.loads( url_opener.open( dir_request ).read() )
        except urllib2.HTTPError, e:
            #print "e", e, url #punting, assuming lack of permissions at this low of a level...
            continue
        break
    if i is not None:
        path = path[i+1:]
    else:
        path = []
    return ( dir_dict, path )

def get_default_directory( url_opener, dm_url ):
    return get_directory( url_opener, dm_url, ["defaultdirectory"] )[0]

def get_personal_directory( url_opener, dm_url ):
    return get_directory( url_opener, dm_url, [ "%s/personaldirectory" % ( GENOMESPACE_API_VERSION_STRING ) ] )[0]

def create_directory( url_opener, directory_dict, new_dir, dm_url ):
    payload = { "isDirectory": True }
    for dir_slice in new_dir:
        if dir_slice in ( '', '/', None ):
            continue
        url = '/'.join( ( directory_dict['url'], urllib.quote( dir_slice.replace( '/', '_' ), safe='' ) ) )
        new_dir_request = urllib2.Request( url, headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' }, data = simplejson.dumps( payload ) )
        new_dir_request.get_method = lambda: 'PUT'
        directory_dict = simplejson.loads( url_opener.open( new_dir_request ).read() )
    return directory_dict

def get_genome_space_launch_apps( atm_url, url_opener, file_url, file_type ):
    gs_request = urllib2.Request( "%s/%s/webtool/descriptor" % ( atm_url, GENOMESPACE_API_VERSION_STRING ) )
    gs_request.get_method = lambda: 'GET'
    opened_gs_request = url_opener.open( gs_request )
    webtool_descriptors = simplejson.loads( opened_gs_request.read() )
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
                #file_name_delimiters = param.get( 'nameDelimiters' )
                if '?' in base_url:
                    url_delimiter = "&"
                else:
                    url_delimiter = "?"
                launch_url = "%s%s%s" % ( base_url, url_delimiter, urllib.urlencode( [ ( file_param_name, file_url ) ] ) )
                webtools.append( ( launch_url, webtool_name ) )
                break
    return webtools
    
def galaxy_code_get_genomespace_folders( genomespace_site='prod', trans=None, value=None, **kwd ):
    if value:
        value = value[0]#single select, only 1 value
    def recurse_directory_dict( url_opener, cur_options, url ):
        cur_directory = urllib2.Request( url )#, headers = { 'Content-Type': 'application/json', 'Accept': 'application/text' } ) #apparently http://www.genomespace.org/team/specs/updated-dm-rest-api:"Every HTTP request to the Data Manager should include the Accept header with a preference for the media types application/json and application/text." is not correct 
        cur_directory.get_method = lambda: 'GET'
        #get url to upload to
        cur_directory =  url_opener.open( cur_directory ).read()
        cur_directory = simplejson.loads( cur_directory )
        directory = cur_directory.get( 'directory', {} )
        contents = cur_directory.get( 'contents', [] )
        if directory.get( 'isDirectory', False ):
            selected = directory.get( 'path' ) == value
            cur_options.append( { 'name':directory.get( 'name' ), 'value': directory.get( 'path'), 'options':[], 'selected': selected  } )
            for sub_dir in contents:
                if sub_dir.get( 'isDirectory', False ):
                    recurse_directory_dict( url_opener, cur_options[-1]['options'], sub_dir.get( 'url' ) )
    rval = []
    if trans and trans.user:
        username = trans.user.preferences.get( 'genomespace_username', None )
        token = trans.user.preferences.get( 'genomespace_token', None )
        if None in ( username, token ):
            return []
        url_opener = get_cookie_opener( username, token )
        genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
        dm_url = genomespace_site_dict['dmServer']
        #get default directory
        directory_dict = get_default_directory( url_opener, dm_url ).get( 'directory', None )
        if directory_dict is None:
            return []
        #what directory to stuff this in
        recurse_directory_dict( url_opener, rval, directory_dict.get( 'url' ) )
    
    return rval
    

def send_file_to_genomespace( genomespace_site, username, token, source_filename, target_directory, target_filename, file_type, content_type, log_filename ):
    url_opener = get_cookie_opener( username, token )
    genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
    dm_url = genomespace_site_dict['dmServer']
    #get default directory
    if target_directory and target_directory[0] == '/':
        directory_dict, target_directory = get_directory( url_opener, dm_url, [ "%s/%s/%s" % ( GENOMESPACE_API_VERSION_STRING, 'file', target_directory[1] ) ] + target_directory[2:] )
        directory_dict = directory_dict['directory']
    else:
        directory_dict = get_personal_directory( url_opener, dm_url )['directory'] #this is the base for the auto-generated galaxy export directories
    #what directory to stuff this in
    target_directory_dict = create_directory( url_opener, directory_dict, target_directory, dm_url )
    #get upload url
    upload_url = "uploadurl"
    content_length = os.path.getsize( source_filename )
    input_file = open( source_filename )
    content_md5 = hashlib.md5()
    chunk_write( input_file, content_md5, target_method="update" )
    input_file.seek( 0 ) #back to start, for uploading

    upload_params = { 'Content-Length': content_length, 'Content-MD5': base64.standard_b64encode( content_md5.digest() ), 'Content-Type': content_type }
    upload_url = "%s/%s/%s%s/%s?%s" % ( dm_url, GENOMESPACE_API_VERSION_STRING, upload_url, target_directory_dict['path'], urllib.quote( target_filename, safe='' ), urllib.urlencode( upload_params ) )
    new_file_request = urllib2.Request( upload_url )#, headers = { 'Content-Type': 'application/json', 'Accept': 'application/text' } ) #apparently http://www.genomespace.org/team/specs/updated-dm-rest-api:"Every HTTP request to the Data Manager should include the Accept header with a preference for the media types application/json and application/text." is not correct 
    new_file_request.get_method = lambda: 'GET'
    #get url to upload to
    target_upload_url = url_opener.open( new_file_request ).read()
    #upload file to determined url
    upload_headers = dict( upload_params )
    #upload_headers[ 'x-amz-meta-md5-hash' ] = content_md5.hexdigest()
    upload_headers[ 'Accept' ] = 'application/json'
    upload_file_request = urllib2.Request( target_upload_url, headers = upload_headers, data = input_file )
    upload_file_request.get_method = lambda: 'PUT'
    upload_result = urllib2.urlopen( upload_file_request ).read()
    
    result_url = "%s/%s" % ( target_directory_dict['url'], urllib.quote( target_filename, safe='' ) )
    #determine available gs launch apps
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
    #Parse Command Line
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
    
    (options, args) = parser.parse_args()
    
    send_file_to_genomespace( options.genomespace_site, options.username, options.token, options.dataset, map( binascii.unhexlify, options.subdirectory ), binascii.unhexlify( options.filename ), options.file_type, options.content_type, options.log )


