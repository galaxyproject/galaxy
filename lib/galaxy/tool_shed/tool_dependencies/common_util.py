import os, shutil, tarfile, urllib2
from galaxy.datatypes.checkers import *

def create_env_var_dict( elem, tool_dependency_install_dir=None, tool_shed_repository_install_dir=None ):
    env_var_name = elem.get( 'name', 'PATH' )
    env_var_action = elem.get( 'action', 'prepend_to' )
    env_var_text = None
    if elem.text and elem.text.find( 'REPOSITORY_INSTALL_DIR' ) >= 0:
        if tool_shed_repository_install_dir:
            env_var_text = elem.text.replace( '$REPOSITORY_INSTALL_DIR', tool_shed_repository_install_dir )
            return dict( name=env_var_name, action=env_var_action, value=env_var_text )
        else:
            env_var_text = elem.text.replace( '$REPOSITORY_INSTALL_DIR', tool_dependency_install_dir )
            return dict( name=env_var_name, action=env_var_action, value=env_var_text )
    if elem.text and elem.text.find( 'INSTALL_DIR' ) >= 0:
        if tool_dependency_install_dir:
            env_var_text = elem.text.replace( '$INSTALL_DIR', tool_dependency_install_dir )
            return dict( name=env_var_name, action=env_var_action, value=env_var_text )
        else:
            env_var_text = elem.text.replace( '$INSTALL_DIR', tool_shed_repository_install_dir )
            return dict( name=env_var_name, action=env_var_action, value=env_var_text )
    return None
def create_or_update_env_shell_file( install_dir, env_var_dict ):
    env_var_name = env_var_dict[ 'name' ]
    env_var_action = env_var_dict[ 'action' ]
    env_var_value = env_var_dict[ 'value' ]
    if env_var_action == 'prepend_to':
        changed_value = '%s:$%s' % ( env_var_value, env_var_name )
    elif env_var_action == 'set_to':
        changed_value = '%s' % env_var_value
    elif env_var_action == 'append_to':
        changed_value = '$%s:%s' % ( env_var_name, env_var_value )
    env_shell_file_path = '%s/env.sh' % install_dir
    if os.path.exists( env_shell_file_path ):
        write_action = '>>'
    else:
        write_action = '>'
    cmd = "echo '%s=%s; export %s' %s %s;chmod +x %s" % ( env_var_name,
                                                          changed_value,
                                                          env_var_name,
                                                          write_action,
                                                          env_shell_file_path,
                                                          env_shell_file_path )
    return cmd
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
def make_directory( full_path ):
    if not os.path.exists( full_path ):
        os.makedirs( full_path )
def move_directory_files( current_dir, source_dir, destination_dir ):
    source_directory = os.path.abspath( os.path.join( current_dir, source_dir ) )
    destination_directory = os.path.join( destination_dir )
    if not os.path.isdir( destination_directory ):
        os.makedirs( destination_directory )
    for file_name in os.listdir( source_directory ):
        source_file = os.path.join( source_directory, file_name )
        destination_file = os.path.join( destination_directory, file_name )
        shutil.move( source_file, destination_file )
def move_file( current_dir, source, destination_dir ):
    source_file = os.path.abspath( os.path.join( current_dir, source ) )
    destination_directory = os.path.join( destination_dir )
    if not os.path.isdir( destination_directory ):
        os.makedirs( destination_directory )
    shutil.move( source_file, destination_directory )
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
