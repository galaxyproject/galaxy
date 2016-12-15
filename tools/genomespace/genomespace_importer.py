# Dan Blankenberg

import json
import optparse
import os
import shutil
import tempfile

from six.moves import http_cookiejar
from six.moves.urllib.parse import parse_qs, unquote_plus, urlparse
from six.moves.urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen

from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry

GENOMESPACE_API_VERSION_STRING = "v1.0"
GENOMESPACE_SERVER_URL_PROPERTIES = "https://dm.genomespace.org/config/%s/serverurl.properties" % ( GENOMESPACE_API_VERSION_STRING )
DEFAULT_GENOMESPACE_TOOLNAME = 'Galaxy'
FILENAME_VALID_CHARS = '.-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '

CHUNK_SIZE = 2**20  # 1mb

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


def get_galaxy_ext_from_genomespace_format_url( url_opener, file_format_url, default=DEFAULT_GALAXY_EXT ):
    ext = GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT.get( file_format_url, None )
    if ext is not None:
        ext = GENOMESPACE_EXT_TO_GALAXY_EXT.get( ext, None )
    if ext is None:
        # could check content type, etc here
        ext = default
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


def download_from_genomespace_importer( username, token, json_parameter_file, genomespace_site, gs_toolname ):
    json_params = json.loads( open( json_parameter_file, 'r' ).read() )
    datasource_params = json_params.get( 'param_dict' )
    assert None not in [ username, token ], "Missing GenomeSpace username or token."
    output_filename = datasource_params.get( "output_file1", None )
    dataset_id = base_dataset_id = json_params['output_data'][0]['dataset_id']
    hda_id = json_params['output_data'][0]['hda_id']
    url_opener = get_cookie_opener( username, token, gs_toolname=gs_toolname )
    # load and set genomespace format ids to galaxy exts
    genomespace_site_dict = get_genomespace_site_urls()[ genomespace_site ]
    set_genomespace_format_identifiers( url_opener, genomespace_site_dict['dmServer'] )
    file_url_name = "URL"
    metadata_parameter_file = open( json_params['job_config']['TOOL_PROVIDED_JOB_METADATA_FILE'], 'wb' )
    # setup datatypes registry for sniffing
    datatypes_registry = Registry()
    datatypes_registry.load_datatypes( root_dir=json_params[ 'job_config' ][ 'GALAXY_ROOT_DIR' ], config=json_params[ 'job_config' ][ 'GALAXY_DATATYPES_CONF_FILE' ] )
    url_param = datasource_params.get( file_url_name, None )
    used_filenames = []
    for download_url in url_param.split( ',' ):
        using_temp_file = False
        parsed_url = urlparse( download_url )
        query_params = parse_qs( parsed_url[4] )
        # write file to disk
        new_file_request = Request( download_url )
        new_file_request.get_method = lambda: 'GET'
        target_download_url = url_opener.open( new_file_request )
        filename = None
        if 'Content-Disposition' in target_download_url.info():
            content_disposition = dict( x.strip().split('=') if '=' in x else ( x.strip(), '' ) for x in target_download_url.info()['Content-Disposition'].split( ';' ) )
            if 'filename' in content_disposition:
                filename = content_disposition[ 'filename' ].strip( "\"'" )
        if not filename:
            parsed_url = urlparse( download_url )
            query_params = parse_qs( parsed_url[4] )
            filename = unquote_plus( parsed_url[2].split( '/' )[-1] )
        if not filename:
            filename = download_url
        if output_filename is None:
            # need to use a temp file here, because we do not know the ext yet
            using_temp_file = True
            output_filename = tempfile.NamedTemporaryFile( prefix='tmp-genomespace-importer-' ).name
        output_file = open( output_filename, 'wb' )
        chunk_write( target_download_url, output_file )
        output_file.close()

        # determine file format
        file_type = None
        if 'dataformat' in query_params:  # this is a converted dataset
            file_type = query_params[ 'dataformat' ][0]
            file_type = get_galaxy_ext_from_genomespace_format_url( url_opener, file_type )
        else:
            try:
                # get and use GSMetadata object
                download_file_path = download_url.split( "%s/file/" % ( genomespace_site_dict['dmServer'] ), 1)[-1]  # FIXME: This is a very bad way to get the path for determining metadata. There needs to be a way to query API using download URLto get to the metadata object
                metadata_request = Request( "%s/%s/filemetadata/%s" % ( genomespace_site_dict['dmServer'], GENOMESPACE_API_VERSION_STRING, download_file_path ) )
                metadata_request.get_method = lambda: 'GET'
                metadata_url = url_opener.open( metadata_request )
                file_metadata_dict = json.loads( metadata_url.read() )
                metadata_url.close()
                file_type = file_metadata_dict.get( 'dataFormat', None )
                if file_type and file_type.get( 'url' ):
                    file_type = file_type.get( 'url' )
                    file_type = get_galaxy_ext_from_genomespace_format_url( url_opener, file_type, default=None )
            except:
                pass
        if file_type is None:
            # try to sniff datatype
            try:
                file_type = sniff.handle_uploaded_dataset_file( output_filename, datatypes_registry )
            except:
                pass  # sniff failed
        if file_type is None and '.' in parsed_url[2]:
            # still no known datatype, fall back to using extension
            file_type = parsed_url[2].rsplit( '.', 1 )[-1]
            file_type = GENOMESPACE_EXT_TO_GALAXY_EXT.get( file_type, file_type )
        if file_type is None:
            # use default extension (e.g. 'data')
            file_type = DEFAULT_GALAXY_EXT

        # save json info for single primary dataset
        if dataset_id is not None:
            metadata_parameter_file.write( "%s\n" % json.dumps( dict( type='dataset',
                                                                      dataset_id=dataset_id,
                                                                      ext=file_type,
                                                                      name="GenomeSpace importer on %s" % ( filename ) ) ) )
        # if using tmp file, move the file to the new file path dir to get scooped up later
        if using_temp_file:
            original_filename = filename
            filename = ''.join( c in FILENAME_VALID_CHARS and c or '-' for c in filename )
            while filename in used_filenames:
                filename = "-%s" % filename
            used_filenames.append( filename )
            target_output_filename = os.path.join( os.getcwd(), 'primary_%i_%s_visible_%s' % ( hda_id, filename, file_type ) )
            shutil.move( output_filename, target_output_filename )
            metadata_parameter_file.write( "%s\n" % json.dumps( dict( type='new_primary_dataset',
                                                                      base_dataset_id=base_dataset_id,
                                                                      ext=file_type,
                                                                      filename=target_output_filename,
                                                                      name="GenomeSpace importer on %s" % ( original_filename ) ) ) )
        dataset_id = None  # only one primary dataset available
        output_filename = None  # only have one filename available
    metadata_parameter_file.close()
    return True


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--json_parameter_file', dest='json_parameter_file', action='store', type="string", default=None, help='json_parameter_file' )
    parser.add_option( '-s', '--genomespace_site', dest='genomespace_site', action='store', type="string", default=None, help='genomespace_site' )
    parser.add_option( '-t', '--token', dest='token', action='store', type="string", default=None, help='token' )
    parser.add_option( '-u', '--username', dest='username', action='store', type="string", default=None, help='username' )
    parser.add_option( '', '--genomespace_toolname', dest='genomespace_toolname', action='store', type="string", default=DEFAULT_GENOMESPACE_TOOLNAME, help='value to use for gs-toolname, used in GenomeSpace internal logging' )
    (options, args) = parser.parse_args()

    download_from_genomespace_importer( options.username, options.token, options.json_parameter_file, options.genomespace_site, options.genomespace_toolname )
