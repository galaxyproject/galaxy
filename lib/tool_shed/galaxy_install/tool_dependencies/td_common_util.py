import logging
import os
import shutil
import sys
import tarfile
import traceback
import urllib2
import zipfile
from string import Template
import tool_shed.util.shed_util_common as suc
from galaxy.datatypes import checkers
from urllib2 import HTTPError

log = logging.getLogger( __name__ )

def clean_tool_shed_url( base_url ):
    if base_url:
        if base_url.find( '://' ) > -1:
            try:
                protocol, base = base_url.split( '://' )
            except ValueError, e:
                # The received base_url must be an invalid url.
                log.debug( "Returning unchanged invalid base_url from td_common_util.clean_tool_shed_url: %s" % str( base_url ) )
                return base_url
            return base.rstrip( '/' )
        return base_url.rstrip( '/' )
    return base_url

def create_env_var_dict( elem, tool_dependency_install_dir=None, tool_shed_repository_install_dir=None ):
    env_var_name = elem.get( 'name', 'PATH' )
    env_var_action = elem.get( 'action', 'prepend_to' )
    env_var_text = None
    if elem.text and elem.text.find( 'REPOSITORY_INSTALL_DIR' ) >= 0:
        if tool_shed_repository_install_dir and elem.text.find( '$REPOSITORY_INSTALL_DIR' ) != -1:
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
    if elem.text:
        # Allow for environment variables that contain neither REPOSITORY_INSTALL_DIR nor INSTALL_DIR since there may be command line
        # parameters that are tuned for a Galaxy instance.  Allowing them to be set in one location rather than being hard coded into
        # each tool config is the best approach.  For example:
        # <environment_variable name="GATK2_SITE_OPTIONS" action="set_to">
        #    "--num_threads 4 --num_cpu_threads_per_data_thread 3 --phone_home STANDARD"
        # </environment_variable>
        return dict( name=env_var_name, action=env_var_action, value=elem.text)
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
    line = "%s=%s; export %s" % (env_var_name, changed_value, env_var_name)
    return create_or_update_env_shell_file_with_command(install_dir, line)


def create_or_update_env_shell_file_with_command( install_dir, command ):
    """
    Return a shell expression which when executed will create or update
    a Galaxy env.sh dependency file in the specified install_dir containing
    the supplied command.
    """
    env_shell_file_path = '%s/env.sh' % install_dir
    if os.path.exists( env_shell_file_path ):
        write_action = '>>'
    else:
        write_action = '>'
    cmd = "echo %s %s %s;chmod +x %s" % ( __shellquote(command),
                                          write_action,
                                          __shellquote(env_shell_file_path),
                                          __shellquote(env_shell_file_path))
    return cmd

def download_binary( url, work_dir ):
    '''
    Download a pre-compiled binary from the specified URL.
    '''
    downloaded_filename = os.path.split( url )[ -1 ]
    dir = url_download( work_dir, downloaded_filename, url, extract=False )
    return downloaded_filename

def extract_tar( file_name, file_path ):
    if isgzip( file_name ) or isbz2( file_name ):
        # Open for reading with transparent compression.
        tar = tarfile.open( file_name, 'r:*', errorlevel=0 )
    else:
        tar = tarfile.open( file_name, errorlevel=0 )
    tar.extractall( path=file_path )
    tar.close()

def extract_zip( archive_path, extraction_path ):
    # TODO: change this method to use zipfile.Zipfile.extractall() when we stop supporting Python 2.5.
    if not zipfile_ok( archive_path ):
        return False
    zip_archive = zipfile.ZipFile( archive_path, 'r' )
    for name in zip_archive.namelist():
        uncompressed_path = os.path.join( extraction_path, name )
        if uncompressed_path.endswith( '/' ):
            if not os.path.isdir( uncompressed_path ):
                os.makedirs( uncompressed_path )
        else:
            file( uncompressed_path, 'wb' ).write( zip_archive.read( name ) )
    zip_archive.close()
    return True

def format_traceback():
    ex_type, ex, tb = sys.exc_info()
    return ''.join( traceback.format_tb( tb ) )

def get_env_shell_file_path( installation_directory ):
    env_shell_file_name = 'env.sh'
    default_location = os.path.abspath( os.path.join( installation_directory, env_shell_file_name ) )
    if os.path.exists( default_location ):
        return default_location
    for root, dirs, files in os.walk( installation_directory ):
        for name in files:
            if name == env_shell_file_name:
                return os.path.abspath( os.path.join( root, name ) )
    return None

def get_env_shell_file_paths( app, elem ):
    # Currently only the following tag set is supported.
    #    <repository toolshed="http://localhost:9009/" name="package_numpy_1_7" owner="test" changeset_revision="c84c6a8be056">
    #        <package name="numpy" version="1.7.1" />
    #    </repository>
    env_shell_file_paths = []
    toolshed = elem.get( 'toolshed', None )
    repository_name = elem.get( 'name', None )
    repository_owner = elem.get( 'owner', None )
    changeset_revision = elem.get( 'changeset_revision', None )
    if toolshed and repository_name and repository_owner and changeset_revision:
        toolshed = clean_tool_shed_url( toolshed )
        repository = suc.get_repository_for_dependency_relationship( app, toolshed, repository_name, repository_owner, changeset_revision )
        if repository:
            for sub_elem in elem:
                tool_dependency_type = sub_elem.tag
                tool_dependency_name = sub_elem.get( 'name' )
                tool_dependency_version = sub_elem.get( 'version' )
                if tool_dependency_type and tool_dependency_name and tool_dependency_version:
                    # Get the tool_dependency so we can get it's installation directory.
                    tool_dependency = None
                    for tool_dependency in repository.tool_dependencies:
                        if tool_dependency.type == tool_dependency_type and tool_dependency.name == tool_dependency_name and tool_dependency.version == tool_dependency_version:
                            break
                    if tool_dependency:
                        tool_dependency_key = '%s/%s' % ( tool_dependency_name, tool_dependency_version )
                        installation_directory = tool_dependency.installation_directory( app )
                        env_shell_file_path = get_env_shell_file_path( installation_directory )
                        if env_shell_file_path:
                            env_shell_file_paths.append( env_shell_file_path )
                        else:
                            error_message = "Skipping tool dependency definition because unable to locate env.sh file for tool dependency "
                            error_message += "type %s, name %s, version %s for repository %s" % \
                                ( str( tool_dependency_type ), str( tool_dependency_name ), str( tool_dependency_version ), str( repository.name ) )
                            log.debug( error_message )
                            continue
                    else:
                        error_message = "Skipping tool dependency definition because unable to locate tool dependency "
                        error_message += "type %s, name %s, version %s for repository %s" % \
                            ( str( tool_dependency_type ), str( tool_dependency_name ), str( tool_dependency_version ), str( repository.name ) )
                        log.debug( error_message )
                        continue
                else:
                    error_message = "Skipping invalid tool dependency definition: type %s, name %s, version %s." % \
                        ( str( tool_dependency_type ), str( tool_dependency_name ), str( tool_dependency_version ) )
                    log.debug( error_message )
                    continue
        else:
            error_message = "Skipping set_environment_for_install definition because unable to locate required installed tool shed repository: "
            error_message += "toolshed %s, name %s, owner %s, changeset_revision %s." % \
                ( str( toolshed ), str( repository_name ), str( repository_owner ), str( changeset_revision ) )
            log.debug( error_message )
    else:
        error_message = "Skipping invalid set_environment_for_install definition: toolshed %s, name %s, owner %s, changeset_revision %s." % \
            ( str( toolshed ), str( repository_name ), str( repository_owner ), str( changeset_revision ) )
        log.debug( error_message )
    return env_shell_file_paths

def get_env_var_values( install_dir ):
    env_var_dict = {}
    env_var_dict[ 'INSTALL_DIR' ] = install_dir
    env_var_dict[ 'system_install' ] = install_dir
    # If the Python interpreter is 64bit then we can safely assume that the underlying system is also 64bit.
    env_var_dict[ '__is64bit__' ] = sys.maxsize > 2**32
    return env_var_dict

def isbz2( file_path ):
    return checkers.is_bz2( file_path )

def isgzip( file_path ):
    return checkers.is_gzip( file_path )

def isjar( file_path ):
    return iszip( file_path ) and file_path.endswith( '.jar' )

def istar( file_path ):
    return tarfile.is_tarfile( file_path )

def iszip( file_path ):
    return checkers.check_zip( file_path )

def is_compressed( file_path ):
    if isjar( file_path ):
        return False
    else:
        return iszip( file_path ) or isgzip( file_path ) or istar( file_path ) or isbz2( file_path )

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

def parse_package_elem( package_elem, platform_info_dict=None, include_after_install_actions=True ):
    """
    Parse a <package> element within a tool dependency definition and return a list of action tuples.  This method is called when setting
    metadata on a repository that includes a tool_dependencies.xml file or when installing a repository that includes a tool_dependencies.xml
    file.  If installing, platform_info_dict must be a valid dictionary and include_after_install_actions must be True.
    """
    # The actions_elem_tuples list contains <actions> tag sets (possibly inside of an <actions_group> tag set) to be processed in the order
    # they are defined in the tool_dependencies.xml file.
    actions_elem_tuples = []
    # The tag sets that will go into the actions_elem_list are those that install a compiled binary if the architecture and operating system
    # match it's defined attributes.  If compiled binary is not installed, the first <actions> tag set [following those that have the os and
    # architecture attributes] that does not have os or architecture attributes will be processed.  This tag set must contain the recipe for
    # downloading and compiling source.
    actions_elem_list = []
    for elem in package_elem:
        if elem.tag == 'actions':
            # We have an <actions> tag that should not be matched against a specific combination of architecture and operating system.
            in_actions_group = False
            actions_elem_tuples.append( ( in_actions_group, elem ) )
        elif elem.tag == 'actions_group':
            # We have an actions_group element, and its child <actions> elements should therefore be compared with the current operating system
            # and processor architecture.
            in_actions_group = True
            # Record the number of <actions> elements so we can filter out any <action> elements that precede <actions> elements.
            actions_elem_count = len( elem.findall( 'actions' ) )
            # Record the number of <actions> elements that have architecture and os specified, in order to filter out any platform-independent
            # <actions> elements that come before platform-specific <actions> elements. This call to elem.findall is filtered by tags that have
            # both the os and architecture specified.  For more details, see http://docs.python.org/2/library/xml.etree.elementtree.html Section
            # 19.7.2.1.
            platform_actions_element_count = len( elem.findall( 'actions[@architecture][@os]' ) )
            platform_actions_elements_processed = 0
            actions_elems_processed = 0
            # The tag sets that will go into the after_install_actions list are <action> tags instead of <actions> tags.  These will be processed
            # only if they are at the very end of the <actions_group> tag set (after all <actions> tag sets). See below for details.
            after_install_actions = []
            # Inspect the <actions_group> element and build the actions_elem_list and the after_install_actions list.
            for child_element in elem:
                if child_element.tag == 'actions':
                    actions_elems_processed += 1
                    system = child_element.get( 'os' )
                    architecture = child_element.get( 'architecture' )
                    # Skip <actions> tags that have only one of architecture or os specified, in order for the count in
                    # platform_actions_elements_processed to remain accurate.
                    if ( system and not architecture ) or ( architecture and not system ):
                        log.debug( 'Error: Both architecture and os attributes must be specified in an <actions> tag.' )
                        continue
                    # Since we are inside an <actions_group> tag set, compare it with our current platform information and filter the <actions>
                    # tag sets that don't match. Require both the os and architecture attributes to be defined in order to find a match.
                    if system and architecture:
                        platform_actions_elements_processed += 1
                        # If either the os or architecture do not match the platform, this <actions> tag will not be considered a match. Skip
                        # it and proceed with checking the next one.
                        if platform_info_dict:
                            if platform_info_dict[ 'os' ] != system or platform_info_dict[ 'architecture' ] != architecture:
                                continue
                        else:
                            # We must not be installing a repository into Galaxy, so determining if we can install a binary is not necessary.
                            continue
                    else:
                        # <actions> tags without both os and architecture attributes are only allowed to be specified after platform-specific
                        # <actions> tags. If we find a platform-independent <actions> tag before all platform-specific <actions> tags have been
                        # processed.
                        if platform_actions_elements_processed < platform_actions_element_count:
                            message = 'Error: <actions> tags without os and architecture attributes are only allowed after all <actions> tags with '
                            message += 'os and architecture attributes have been defined. Skipping the <actions> tag set with no os or architecture '
                            message += 'attributes that has been defined between two <actions> tag sets that have these attributes defined.  '
                            log.debug( message )
                            continue
                    # If we reach this point, it means one of two things: 1) The system and architecture attributes are not defined in this
                    # <actions> tag, or 2) The system and architecture attributes are defined, and they are an exact match for the current
                    # platform. Append the child element to the list of elements to process.
                    actions_elem_list.append( child_element )
                elif child_element.tag == 'action':
                    # Any <action> tags within an <actions_group> tag set must come after all <actions> tags. 
                    if actions_elems_processed == actions_elem_count:
                        # If all <actions> elements have been processed, then this <action> element can be appended to the list of actions to
                        # execute within this group.
                        after_install_actions.append( child_element )
                    else:
                        # If any <actions> elements remain to be processed, then log a message stating that <action> elements are not allowed
                        # to precede any <actions> elements within an <actions_group> tag set.
                        message = 'Error: <action> tags are only allowed at the end of an <actions_group> tag set after all <actions> tags.  '
                        message += 'Skipping <%s> element with type %s.' % ( child_element.tag, child_element.get( 'type' ) )
                        log.debug( message )
                        continue
            if platform_info_dict is None and not include_after_install_actions:
                # We must be setting metadata on a repository.
                actions_elem_tuples.append( ( in_actions_group, actions_elem_list[ 0 ] ) )
            elif platform_info_dict is not None and include_after_install_actions:
                # We must be installing a repository.
                if after_install_actions:
                    actions_elem_list.extend( after_install_actions )
                actions_elem_tuples.append( ( in_actions_group, actions_elem_list ) )
        else:
            # Skip any element that is not <actions> or <actions_group> - this will skip comments, <repository> tags and <readme> tags.
            in_actions_group = False
            continue
    return actions_elem_tuples

def tar_extraction_directory( file_path, file_name ):
    """Try to return the correct extraction directory."""
    file_name = file_name.strip()
    extensions = [ '.tar.gz', '.tgz', '.tar.bz2', '.tar', '.zip' ]
    for extension in extensions:
        if file_name.find( extension ) > 0:
            dir_name = file_name[ :-len( extension ) ]
            if os.path.exists( os.path.abspath( os.path.join( file_path, dir_name ) ) ):
                return dir_name
    if os.path.exists( os.path.abspath( os.path.join( file_path, file_name ) ) ):
        return os.path.abspath( file_path )
    raise ValueError( 'Could not find path to file %s' % os.path.abspath( os.path.join( file_path, file_name ) ) )

def url_download( install_dir, downloaded_file_name, download_url, extract=True ):
    file_path = os.path.join( install_dir, downloaded_file_name )
    src = None
    dst = None
    try:
        src = urllib2.urlopen( download_url )
        dst = open( file_path, 'wb' )
        while True:
            chunk = src.read( suc.CHUNK_SIZE )
            if chunk:
                dst.write( chunk )
            else:
                break
    except:
        raise
    finally:
        if src:
            src.close()
        if dst:
            dst.close()
    if extract:
        if istar( file_path ):
            # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
            extract_tar( file_path, install_dir )
            dir = tar_extraction_directory( install_dir, downloaded_file_name )
        elif isjar( file_path ):
            dir = os.path.curdir
        elif iszip( file_path ):
            # <action type="download_by_url">http://downloads.sourceforge.net/project/picard/picard-tools/1.56/picard-tools-1.56.zip</action>
            zip_archive_extracted = extract_zip( file_path, install_dir )
            dir = zip_extraction_directory( install_dir, downloaded_file_name )
        else:
            dir = os.path.abspath( install_dir )
    else:
        dir = os.path.abspath( install_dir )
    return dir

def zip_extraction_directory( file_path, file_name ):
    """Try to return the correct extraction directory."""
    files = [ filename for filename in os.listdir( file_path ) if not filename.endswith( '.zip' ) ]
    if len( files ) > 1:
        return os.path.abspath( file_path )
    elif len( files ) == 1:
        # If there is only on file it should be a directory.
        if os.path.isdir( os.path.join( file_path, files[ 0 ] ) ):
            return os.path.abspath( os.path.join( file_path, files[ 0 ] ) )
    raise ValueError( 'Could not find directory for the extracted file %s' % os.path.abspath( os.path.join( file_path, file_name ) ) )

def zipfile_ok( path_to_archive ):
    """
    This function is a bit pedantic and not functionally necessary.  It checks whether there is no file pointing outside of the extraction,
    because ZipFile.extractall() has some potential security holes.  See python zipfile documentation for more details.
    """
    basename = os.path.realpath( os.path.dirname( path_to_archive ) )
    zip_archive = zipfile.ZipFile( path_to_archive )
    for member in zip_archive.namelist():
        member_path = os.path.realpath( os.path.join( basename, member ) )
        if not member_path.startswith( basename ):
            return False
    return True

def __shellquote(s):
    """Quote and escape the supplied string for use in shell expressions."""
    return "'" + s.replace( "'", "'\\''" ) + "'"

def evaluate_template( text, install_dir ):
    """ Substitute variables defined in XML blocks from dependencies file."""
    return Template( text ).safe_substitute( get_env_var_values( install_dir ) )

