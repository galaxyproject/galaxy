# Dan Blankenberg
import json
import optparse
import os

from six.moves import http_cookiejar
from six.moves.urllib.parse import unquote_plus, urlencode, urlparse
from six.moves.urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen

from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry

GENOMESPACE_API_VERSION_STRING = "v1.0"
GENOMESPACE_SERVER_URL_PROPERTIES = "https://dm.genomespace.org/config/%s/serverurl.properties" % ( GENOMESPACE_API_VERSION_STRING )
DEFAULT_GENOMESPACE_TOOLNAME = 'Galaxy'
FILENAME_VALID_CHARS = '.-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '

CHUNK_SIZE = 2**20  # 1mb

AUTO_GALAXY_EXT = "auto"
DEFAULT_GALAXY_EXT = "data"

# genomespace format identifier is the URL
GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT = {}  # TODO: fix this so it is not a global variable
# TODO: we should use a better way to set up this mapping
GENOMESPACE_EXT_TO_GALAXY_EXT = {'rifles': 'rifles',
                                 'lifes': 'lifes',
                                 'cn': 'cn',
                                 'GTF': 'gtf',
                                 'res': 'res',
                                 'xcn': 'xcn',
                                 'lowercasetxt': 'lowercasetxt',
                                 'bed': 'bed',
                                 'CBS': 'cbs',
                                 'genomicatab': 'genomicatab',
                                 'gxp': 'gxp',
                                 'reversedtxt': 'reversedtxt',
                                 'nowhitespace': 'nowhitespace',
                                 'unknown': 'unknown',
                                 'txt': 'txt',
                                 'uppercasetxt': 'uppercasetxt',
                                 'GISTIC': 'gistic',
                                 'GFF': 'gff',
                                 'gmt': 'gmt',
                                 'gct': 'gct'}

GENOMESPACE_UNKNOWN_FORMAT_KEY = 'unknown'
GENOMESPACE_FORMAT_IDENTIFIER_UNKNOWN = None


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


def get_galaxy_ext_from_genomespace_format_url( url_opener, file_format_url ):
    ext = GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT.get( file_format_url, None )
    if ext is not None:
        ext = GENOMESPACE_EXT_TO_GALAXY_EXT.get( ext, None )
    if ext is None:
        # could check content type, etc here
        ext = AUTO_GALAXY_EXT
    return ext


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


def set_genomespace_format_identifiers( url_opener, dm_site ):
    gs_request = Request( "%s/%s/dataformat/list" % ( dm_site, GENOMESPACE_API_VERSION_STRING ) )
    gs_request.get_method = lambda: 'GET'
    opened_gs_request = url_opener.open( gs_request )
    genomespace_formats = json.loads( opened_gs_request.read() )
    for format in genomespace_formats:
        GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT[ format['url'] ] = format['name']
    global GENOMESPACE_FORMAT_IDENTIFIER_UNKNOWN
    GENOMESPACE_FORMAT_IDENTIFIER_UNKNOWN = dict( ( x[1], x[0] ) for x in GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT.items() ).get( GENOMESPACE_UNKNOWN_FORMAT_KEY, GENOMESPACE_FORMAT_IDENTIFIER_UNKNOWN )


def download_from_genomespace_file_browser( json_parameter_file, genomespace_site, gs_toolname ):
    json_params = json.loads( open( json_parameter_file, 'r' ).read() )
    datasource_params = json_params.get( 'param_dict' )
    username = datasource_params.get( "gs-username", None )
    token = datasource_params.get( "gs-token", None )
    assert None not in [ username, token ], "Missing GenomeSpace username or token."
    output_filename = datasource_params.get( "output", None )
    dataset_id = json_params['output_data'][0]['dataset_id']
    hda_id = json_params['output_data'][0]['hda_id']
    url_opener = get_cookie_opener( username, token, gs_toolname=gs_toolname )
    # load and set genomespace format ids to galaxy exts
    genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
    set_genomespace_format_identifiers( url_opener, genomespace_site_dict['dmServer'] )

    file_url_prefix = "fileUrl"
    file_type_prefix = "fileFormat"
    metadata_parameter_file = open( json_params['job_config']['TOOL_PROVIDED_JOB_METADATA_FILE'], 'wb' )

    # setup datatypes registry for sniffing
    datatypes_registry = Registry()
    datatypes_registry.load_datatypes( root_dir=json_params[ 'job_config' ][ 'GALAXY_ROOT_DIR' ], config=json_params[ 'job_config' ][ 'GALAXY_DATATYPES_CONF_FILE' ] )

    file_numbers = []
    for name in datasource_params.keys():
        if name.startswith( file_url_prefix ):
            name = name[len( file_url_prefix ):]
            file_numbers.append( int( name ) )
    if not file_numbers:
        if output_filename:
            open( output_filename, 'wb' )  # erase contents of file
        raise Exception( "You must select at least one file to import into Galaxy." )
    file_numbers.sort()
    used_filenames = []
    for file_num in file_numbers:
        url_key = "%s%i" % ( file_url_prefix, file_num )
        download_url = datasource_params.get( url_key, None )
        if download_url is None:
            break
        filetype_key = "%s%i" % ( file_type_prefix, file_num )
        filetype_url = datasource_params.get( filetype_key, None )
        galaxy_ext = get_galaxy_ext_from_genomespace_format_url( url_opener, filetype_url )
        formatted_download_url = "%s?%s" % ( download_url, urlencode( [ ( 'dataformat', filetype_url ) ] ) )
        new_file_request = Request( formatted_download_url )
        new_file_request.get_method = lambda: 'GET'
        target_download_url = url_opener.open( new_file_request )
        filename = None
        if 'Content-Disposition' in target_download_url.info():
            # If the response has Content-Disposition, try to get filename from it
            content_disposition = dict( x.strip().split('=') if '=' in x else ( x.strip(), '' ) for x in target_download_url.info()['Content-Disposition'].split( ';' ) )
            if 'filename' in content_disposition:
                filename = content_disposition[ 'filename' ].strip( "\"'" )
        if not filename:
            parsed_url = urlparse( download_url )
            filename = unquote_plus( parsed_url[2].split( '/' )[-1] )
        if not filename:
            filename = download_url
        metadata_dict = None
        original_filename = filename
        if output_filename is None:
            filename = ''.join( c in FILENAME_VALID_CHARS and c or '-' for c in filename )
            while filename in used_filenames:
                filename = "-%s" % filename
            used_filenames.append( filename )
            output_filename = os.path.join( os.getcwd(), 'primary_%i_%s_visible_%s' % ( hda_id, filename, galaxy_ext ) )

            metadata_dict = dict( type='new_primary_dataset',
                                  base_dataset_id=dataset_id,
                                  ext=galaxy_ext,
                                  filename=output_filename,
                                  name="GenomeSpace import on %s" % ( original_filename ) )
        else:
            if dataset_id is not None:
                metadata_dict = dict( type='dataset',
                                      dataset_id=dataset_id,
                                      ext=galaxy_ext,
                                      name="GenomeSpace import on %s" % ( filename ) )
        output_file = open( output_filename, 'wb' )
        chunk_write( target_download_url, output_file )
        output_file.close()

        if ( galaxy_ext == AUTO_GALAXY_EXT or filetype_url == GENOMESPACE_FORMAT_IDENTIFIER_UNKNOWN ) and metadata_dict:
            # try to sniff datatype
            try:
                galaxy_ext = sniff.handle_uploaded_dataset_file( output_filename, datatypes_registry )
            except:
                # sniff failed
                galaxy_ext = original_filename.rsplit( '.', 1 )[-1]
                if galaxy_ext not in datatypes_registry.datatypes_by_extension:
                    galaxy_ext = DEFAULT_GALAXY_EXT
            metadata_dict[ 'ext' ] = galaxy_ext

        output_filename = None  # only have one filename available

        # write out metadata info
        if metadata_dict:
            metadata_parameter_file.write( "%s\n" % json.dumps( metadata_dict ) )

    metadata_parameter_file.close()
    return True


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--json_parameter_file', dest='json_parameter_file', action='store', type="string", default=None, help='json_parameter_file' )
    parser.add_option( '-s', '--genomespace_site', dest='genomespace_site', action='store', type="string", default=None, help='genomespace_site' )
    parser.add_option( '', '--genomespace_toolname', dest='genomespace_toolname', action='store', type="string", default=DEFAULT_GENOMESPACE_TOOLNAME, help='value to use for gs-toolname, used in GenomeSpace internal logging' )
    (options, args) = parser.parse_args()

    download_from_genomespace_file_browser( options.json_parameter_file, options.genomespace_site, options.genomespace_toolname )
