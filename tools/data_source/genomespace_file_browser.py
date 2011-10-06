#Dan Blankenberg

import optparse, os, urllib2, cookielib

from galaxy import eggs
import pkg_resources

pkg_resources.require( "simplejson" )
import simplejson

CHUNK_SIZE = 2**20 #1mb

DEFAULT_GALAXY_EXT = "data"

#genomespace format identifier is the URL
GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT = { 'http://www.genomespace.org/datamanager/dataformat/res/0.0.0': 'res', 
                                               'http://www.genomespace.org/datamanager/dataformat/cbs/0.0.0': 'CBS', 
                                               'http://www.genomespace.org/datamanager/dataformat/lowercasetxt/0.0.0': 'lowercasetxt', 
                                               'http://www.genomespace.org/datamanager/dataformat/gff/0.0.0': 'GFF', 
                                               'http://www.genomespace.org/datamanager/dataformat/reversedtxt/0.0.0': 'reversedtxt', 
                                               'http://www.genomespace.org/datamanager/dataformat/gxp/0.0.0': 'gxp', 
                                               'http://www.genomespace.org/datamanager/dataformat/unknown/0.0.0': 'unknown', 
                                               'http://www.genomespace.org/datamanager/dataformat/gtf/0.0.0': 'GTF', 
                                               'http://www.genomespace.org/datamanager/dataformat/cn/0.0.0': 'cn', 
                                               'http://www.genomespace.org/datamanager/dataformat/gct/0.0.0': 'gct', 
                                               'http://www.genomespace.org/datamanager/dataformat/nowhitespace/0.0.0': 'nowhitespace', 
                                               'http://www.genomespace.org/datamanager/dataformat/gistic/0.0.0': 'GISTIC', 
                                               'http://www.genomespace.org/datamanager/dataformat/rifles/0.0.0': 'rifles', 
                                               'http://www.genomespace.org/datamanager/dataformat/bed/0.0.0': 'bed', 
                                               'http://www.genomespace.org/datamanager/dataformat/txt/0.0.0': 'txt', 
                                               'http://www.genomespace.org/datamanager/dataformat/uppercasetxt/0.0.0': 'uppercasetxt', 
                                               'http://www.genomespace.org/datamanager/dataformat/xcn/0.0.0': 'xcn', 
                                               'http://www.genomespace.org/datamanager/dataformat/gmt/0.0.0': 'gmt', 
                                               'http://www.genomespace.org/datamanager/dataformat/genomicatab/0.0.0': 'genomicatab', 
                                               'http://www.genomespace.org/datamanager/dataformat/lifes/0.0.0': 'lifes' }

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
                                 'txt': 'txt', 'uppercasetxt': 
                                 'uppercasetxt', 
                                 'GISTIC': 'gistic', 
                                 'GFF': 'gff', 
                                 'gmt': 'gmt', 
                                 'gct': 'gct'}

'''
https://dmdev.genomespace.org:8444/datamanager/dataformat/list
from galaxy import eggs
import pkg_resources
pkg_resources.require( "simplejson" )
import simplejson
formats = simplejson.loads( '[{"name":"GISTIC","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gistic\/0.0.0","fileExtension":"gistic"},{"name":"GFF","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gff\/0.0.0","fileExtension":"seg"},{"name":"gct","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gct\/0.0.0","fileExtension":"gct"},{"name":"lifes","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/lifes\/0.0.0","fileExtension":"lifes"},{"name":"GTF","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gtf\/0.0.0","fileExtension":"gtf"},{"name":"rifles","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/rifles\/0.0.0","fileExtension":"rifles"},{"name":"CBS","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/cbs\/0.0.0","fileExtension":"cbs"},{"name":"unknown","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/unknown\/0.0.0"},{"name":"reversedtxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/reversedtxt\/0.0.0","fileExtension":"reversedtxt"},{"name":"res","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/res\/0.0.0","fileExtension":"res"},{"name":"cn","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/cn\/0.0.0","fileExtension":"cn"},{"name":"gmt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gmt\/0.0.0","fileExtension":"gmt"},{"name":"bed","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/bed\/0.0.0","fileExtension":"bed"},{"name":"gxp","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gxp\/0.0.0","fileExtension":"gxp"},{"name":"uppercasetxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/uppercasetxt\/0.0.0","fileExtension":"uppertxt"},{"name":"lowercasetxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/lowercasetxt\/0.0.0","fileExtension":"lowertxt"},{"name":"genomicatab","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/genomicatab\/0.0.0","fileExtension":"tab"},{"name":"nowhitespace","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/nowhitespace\/0.0.0","fileExtension":"nowhitespace"},{"name":"xcn","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/xcn\/0.0.0","fileExtension":"xcn"},{"name":"txt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/txt\/0.0.0","fileExtension":"txt"}]' )
formats = [{"name":"GISTIC","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gistic\/0.0.0","fileExtension":"gistic"},{"name":"GFF","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gff\/0.0.0","fileExtension":"seg"},{"name":"gct","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gct\/0.0.0","fileExtension":"gct"},{"name":"lifes","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/lifes\/0.0.0","fileExtension":"lifes"},{"name":"GTF","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gtf\/0.0.0","fileExtension":"gtf"},{"name":"rifles","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/rifles\/0.0.0","fileExtension":"rifles"},{"name":"CBS","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/cbs\/0.0.0","fileExtension":"cbs"},{"name":"unknown","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/unknown\/0.0.0"},{"name":"reversedtxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/reversedtxt\/0.0.0","fileExtension":"reversedtxt"},{"name":"res","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/res\/0.0.0","fileExtension":"res"},{"name":"cn","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/cn\/0.0.0","fileExtension":"cn"},{"name":"gmt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gmt\/0.0.0","fileExtension":"gmt"},{"name":"bed","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/bed\/0.0.0","fileExtension":"bed"},{"name":"gxp","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/gxp\/0.0.0","fileExtension":"gxp"},{"name":"uppercasetxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/uppercasetxt\/0.0.0","fileExtension":"uppertxt"},{"name":"lowercasetxt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/lowercasetxt\/0.0.0","fileExtension":"lowertxt"},{"name":"genomicatab","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/genomicatab\/0.0.0","fileExtension":"tab"},{"name":"nowhitespace","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/nowhitespace\/0.0.0","fileExtension":"nowhitespace"},{"name":"xcn","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/xcn\/0.0.0","fileExtension":"xcn"},{"name":"txt","version":"0.0.0","url":"http:\/\/www.genomespace.org\/datamanager\/dataformat\/txt\/0.0.0","fileExtension":"txt"}]
GENOMESPACE_FORMAT_IDENTIFIER_TO_GALAXY_EXT = {}
for format in formats:
    GENOMESPACE_FORMAT_IDENTIFIER_TO_GALAXY_EXT[ format[ 'url' ] ] = format['name']

print GENOMESPACE_FORMAT_IDENTIFIER_TO_GALAXY_EXT
#do manual change to galaxy exts
'''


def chunk_write( source_stream, target_stream, source_method = "read", target_method="write" ):
    source_method = getattr( source_stream, source_method )
    target_method = getattr( target_stream, target_method )
    while True:
        chunk = source_method( CHUNK_SIZE )
        if chunk:
            target_method( chunk )
        else:
            break

def get_cookie_opener( gs_username, gs_token  ):
    """ Create a GenomeSpace cookie opener """
    cj = cookielib.CookieJar()
    for cookie_name, cookie_value in [ ( 'gs-token', gs_token ), ( 'gs-username', gs_username ) ]:
        #create a super-cookie, valid for all domains
        cookie = cookielib.Cookie(version=0, name=cookie_name, value=cookie_value, port=None, port_specified=False, domain='', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False )
        cj.set_cookie( cookie )
    cookie_opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( cj ) )
    return cookie_opener

def get_galaxy_ext_from_genomespace_format_url( url_opener, file_format_url ):
    ext = GENOMESPACE_FORMAT_IDENTIFIER_TO_GENOMESPACE_EXT.get( file_format_url, None )
    if ext is not None:
        ext = GENOMESPACE_EXT_TO_GALAXY_EXT.get( ext, None )
    if ext is None:
        #could check content type, etc here
        ext = DEFAULT_GALAXY_EXT
    return ext

def download_from_genomespace_file_browser( json_parameter_file ):
    json_params = simplejson.loads( open( json_parameter_file, 'r' ).read() )
    datasource_params = json_params.get( 'param_dict' )
    username = datasource_params.get( "gs-username", None )
    token = datasource_params.get( "gs-token", None )
    assert None not in [ username, token ], "Missing GenomeSpace username or token."
    output_filename = datasource_params.get( "output", None )
    dataset_id = json_params['output_data'][0]['dataset_id']
    url_opener = get_cookie_opener( username, token )
    file_count = 1
    file_url_prefix = "fileUrl"
    file_type_prefix = "fileFormat"
    metadata_parameter_file = open( json_params['job_config']['TOOL_PROVIDED_JOB_METADATA_FILE'], 'wb' )
    file_numbers = []
    for name in datasource_params.keys():
        if name.startswith( file_url_prefix ):
            name = name[len( file_url_prefix ):]
            file_numbers.append( int( name ) )
    file_numbers.sort()
    print 'file_numbers', file_numbers
    #print 'datasource_params', datasource_params
    for file_num in file_numbers:
        url_key = "%s%i" % ( file_url_prefix, file_num )
        download_url = datasource_params.get( url_key, None )
        if download_url is None:
            print 'wtf none', file_num
            break
        filetype_key = "%s%i" % ( file_type_prefix, file_num )
        filetype_url = datasource_params.get( filetype_key, None )
        galaxy_ext = get_galaxy_ext_from_genomespace_format_url( url_opener, filetype_url )
        if output_filename is None:
            output_filename = os.path.join( datasource_params['__new_file_path__'],  'primary_%i_output%i_visible_%s' % ( dataset_id, file_count, galaxy_ext ) )
        else:
            if dataset_id is not None:
               metadata_parameter_file.write( "%s\n" % simplejson.dumps( dict( type = 'dataset',
                                     dataset_id = dataset_id,
                                     ext = galaxy_ext ) ) )
        output_file = open( output_filename, 'wb' )
        new_file_request = urllib2.Request( download_url )
        new_file_request.get_method = lambda: 'GET'
        target_download_url = url_opener.open( new_file_request )
        chunk_write( target_download_url, output_file )
        output_file.close()
        output_filename = None #only have one filename available
    metadata_parameter_file.close()
    return True

if __name__ == '__main__':
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--json_parameter_file', dest='json_parameter_file', action='store', type="string", default=None, help='json_parameter_file' )
    (options, args) = parser.parse_args()
    
    download_from_genomespace_file_browser( options.json_parameter_file )
