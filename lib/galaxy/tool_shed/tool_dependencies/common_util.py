import os, tarfile, urllib2
from galaxy.datatypes.checkers import *

def extract_tar( file_name, file_path ):
    if isgzip( file_name ) or isbz2( file_name ):
        # Open for reading with transparent compression.
        tar = tarfile.open( file_name, 'r:*' )
    else:
        tar = tarfile.open( file_name )
    tar.extractall( path=file_path )
    tar.close()
def isbz2( file_path ):
    return is_bz2( file_path )
def isgzip( file_path ):
    return is_gzip( file_path )
def istar( file_path ):
    return tarfile.is_tarfile( file_path )
def iszip( file_path ):
    return check_zip( file_path )
def tar_extraction_directory( file_path, file_name ):
    file_name = file_name.strip()
    extensions = [ '.tar.gz', '.tgz', '.tar.bz2', '.zip' ]
    for extension in extensions:
        if file_name.find( extension ) > 0:
            dir_name = file_name[ :-len( extension ) ]
            if os.path.exists( os.path.abspath( os.path.join( file_path, dir_name ) ) ):
                return dir_name
    if os.path.exists( os.path.abspath( os.path.join( file_path, file_name ) ) ):
        return os.path.abspath( os.path.join( file_path, file_name ) )
    raise ValueError( 'Could not find directory %s' % os.path.abspath( os.path.join( file_path, file_name[ :-len( extension ) ] ) ) )
def url_download( install_dir, downloaded_file_name, download_url ):
    file_path = os.path.join( install_dir, downloaded_file_name )
    src = None
    dst = None
    try:
        src = urllib2.urlopen( download_url )
        data = src.read()
        dst = open( file_path,'wb' )
        dst.write( data )
    except:
        if src:
            src.close()
        if dst:
            dst.close()
    return os.path.abspath( file_path )
