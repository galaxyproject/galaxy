import logging
import os
import re
import shutil
import stat
import sys
import tarfile
import time
import traceback
import urllib2
import zipfile
from string import Template
from tool_shed.util import common_util
import tool_shed.util.shed_util_common as suc
from galaxy.datatypes import checkers

log = logging.getLogger( __name__ )

# Set no activity timeout to 20 minutes.
NO_OUTPUT_TIMEOUT = 1200.0
INSTALLATION_LOG = 'INSTALLATION.log'


class CompressedFile( object ):

    def __init__( self, file_path, mode='r' ):
        if istar( file_path ):
            self.file_type = 'tar'
        elif iszip( file_path ) and not isjar( file_path ):
            self.file_type = 'zip'
        self.file_name = os.path.splitext( os.path.basename( file_path ) )[ 0 ]
        if self.file_name.endswith( '.tar' ):
            self.file_name = os.path.splitext( self.file_name )[ 0 ]
        self.type = self.file_type
        method = 'open_%s' % self.file_type
        if hasattr( self, method ):
            self.archive = getattr( self, method )( file_path, mode )
        else:
            raise NameError( 'File type %s specified, no open method found.' % self.file_type )

    def extract( self, path ):
        '''Determine the path to which the archive should be extracted.'''
        contents = self.getmembers()
        extraction_path = path
        if len( contents ) == 1:
            # The archive contains a single file, return the extraction path.
            if self.isfile( contents[ 0 ] ):
                extraction_path = os.path.join( path, self.file_name )
                if not os.path.exists( extraction_path ):
                    os.makedirs( extraction_path )
                self.archive.extractall( extraction_path )
        else:
            # Get the common prefix for all the files in the archive. If the common prefix ends with a slash,
            # or self.isdir() returns True, the archive contains a single directory with the desired contents.
            # Otherwise, it contains multiple files and/or directories at the root of the archive.
            common_prefix = os.path.commonprefix( [ self.getname( item ) for item in contents ] )
            if len( common_prefix ) >= 1 and not common_prefix.endswith( os.sep ) and self.isdir( self.getmember( common_prefix ) ):
                common_prefix += os.sep
            if common_prefix.endswith( os.sep ):
                self.archive.extractall( os.path.join( path ) )
                extraction_path = os.path.join( path, common_prefix )
            else:
                extraction_path = os.path.join( path, self.file_name )
                if not os.path.exists( extraction_path ):
                    os.makedirs( extraction_path )
                self.archive.extractall( os.path.join( extraction_path ) )
        return os.path.abspath( extraction_path )

    def getmembers_tar( self ):
        return self.archive.getmembers()

    def getmembers_zip( self ):
        return self.archive.infolist()

    def getname_tar( self, item ):
        return item.name

    def getname_zip( self, item ):
        return item.filename

    def getmember( self, name ):
        for member in self.getmembers():
            if self.getname( member ) == name:
                return member

    def getmembers( self ):
        return getattr( self, 'getmembers_%s' % self.type )()

    def getname( self, member ):
        return getattr( self, 'getname_%s' % self.type )( member )

    def isdir( self, member ):
        return getattr( self, 'isdir_%s' % self.type )( member )

    def isdir_tar( self, member ):
        return member.isdir()

    def isdir_zip( self, member ):
        if member.filename.endswith( os.sep ):
            return True
        return False

    def isfile( self, member ):
        if not self.isdir( member ):
            return True
        return False

    def open_tar( self, filepath, mode ):
        return tarfile.open( filepath, mode, errorlevel=0 )

    def open_zip( self, filepath, mode ):
        return zipfile.ZipFile( filepath, mode )

def assert_directory_executable( full_path ):
    """
    Return True if a symbolic link or directory exists and is executable, but if
    full_path is a file, return False.
    """
    if full_path is None:
        return False
    if os.path.isfile( full_path ):
        return False
    if os.path.isdir( full_path ):
        # Make sure the owner has execute permission on the directory.
        # See http://docs.python.org/2/library/stat.html
        if stat.S_IXUSR & os.stat( full_path )[ stat.ST_MODE ] == 64:
            return True
    return False

def assert_directory_exists( full_path ):
    """
    Return True if a symbolic link or directory exists, but if full_path is a file,
    return False.    """
    if full_path is None:
        return False
    if os.path.isfile( full_path ):
        return False
    if os.path.isdir( full_path ):
        return True
    return False

def assert_file_executable( full_path ):
    """
    Return True if a symbolic link or file exists and is executable, but if full_path
    is a directory, return False.
    """
    if full_path is None:
        return False
    if os.path.isdir( full_path ):
        return False
    if os.path.exists( full_path ):
        # Make sure the owner has execute permission on the file.
        # See http://docs.python.org/2/library/stat.html
        if stat.S_IXUSR & os.stat( full_path )[ stat.ST_MODE ] == 64:
            return True
    return False

def assert_file_exists( full_path ):
    """
    Return True if a symbolic link or file exists, but if full_path is a directory,
    return False.
    """
    if full_path is None:
        return False
    if os.path.isdir( full_path ):
        return False
    if os.path.exists( full_path ):
        return True
    return False

def create_env_var_dict( elem, install_environment ):
    env_var_name = elem.get( 'name', 'PATH' )
    env_var_action = elem.get( 'action', 'prepend_to' )
    env_var_text = None
    tool_dependency_install_dir = install_environment.install_dir
    tool_shed_repository_install_dir = install_environment.tool_shed_repository_install_dir
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
        # Allow for environment variables that contain neither REPOSITORY_INSTALL_DIR nor INSTALL_DIR
        # since there may be command line parameters that are tuned for a Galaxy instance.  Allowing them
        # to be set in one location rather than being hard coded into each tool config is the best approach.
        # For example:
        # <environment_variable name="GATK2_SITE_OPTIONS" action="set_to">
        #    "--num_threads 4 --num_cpu_threads_per_data_thread 3 --phone_home STANDARD"
        # </environment_variable>
        return dict( name=env_var_name, action=env_var_action, value=elem.text)
    return None

def download_binary( url, work_dir ):
    """Download a pre-compiled binary from the specified URL."""
    downloaded_filename = os.path.split( url )[ -1 ]
    dir = url_download( work_dir, downloaded_filename, url, extract=False )
    return downloaded_filename

def egrep_escape( text ):
    """Escape ``text`` to allow literal matching using egrep."""
    regex = re.escape( text )
    # Seems like double escaping is needed for \
    regex = regex.replace( '\\\\', '\\\\\\' )
    # Triple-escaping seems to be required for $ signs
    regex = regex.replace( r'\$', r'\\\$' )
    # Whereas single quotes should not be escaped
    regex = regex.replace( r"\'", "'" )
    return regex

def evaluate_template( text, install_environment ):
    """
    Substitute variables defined in XML blocks from dependencies file.  The value of the received
    repository_install_dir is the root installation directory of the repository that contains the
    tool dependency.  The value of the received install_dir is the root installation directory of
    the tool_dependency.
    """
    return Template( text ).safe_substitute( get_env_var_values( install_environment ) )

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
         # The protocol is not stored, but the port is if it exists.
        toolshed = common_util.remove_protocol_from_tool_shed_url( toolshed )
        repository = suc.get_repository_for_dependency_relationship( app, toolshed, repository_name, repository_owner, changeset_revision )
        if repository:
            for sub_elem in elem:
                tool_dependency_type = sub_elem.tag
                tool_dependency_name = sub_elem.get( 'name' )
                tool_dependency_version = sub_elem.get( 'version' )
                if tool_dependency_type and tool_dependency_name and tool_dependency_version:
                    # Get the tool_dependency so we can get its installation directory.
                    tool_dependency = None
                    for tool_dependency in repository.tool_dependencies:
                        if tool_dependency.type == tool_dependency_type and \
                            tool_dependency.name == tool_dependency_name and \
                            tool_dependency.version == tool_dependency_version:
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

def get_env_shell_file_paths_from_setup_environment_elem( app, all_env_shell_file_paths, elem, action_dict ):
    """
    Parse an XML tag set to discover all child repository dependency tags and define the path to an env.sh file associated
    with the repository (this requires the repository dependency to be in an installed state).  The received action_dict
    will be updated with these discovered paths and returned to the caller.  This method handles tool dependency definition
    tag sets <setup_r_environment>, <setup_ruby_environment> and <setup_perl_environment>.
    """
    # An example elem is:
    # <action type="setup_perl_environment">
    #     <repository name="package_perl_5_18" owner="iuc">
    #         <package name="perl" version="5.18.1" />
    #     </repository>
    #     <repository name="package_expat_2_1" owner="iuc" prior_installation_required="True">
    #         <package name="expat" version="2.1.0" />
    #     </repository>
    #     <package>http://search.cpan.org/CPAN/authors/id/T/TO/TODDR/XML-Parser-2.41.tar.gz</package>
    #     <package>http://search.cpan.org/CPAN/authors/id/L/LD/LDS/CGI.pm-3.43.tar.gz</package>
    # </action>
    for action_elem in elem:
        if action_elem.tag == 'repository':
            env_shell_file_paths = get_env_shell_file_paths( app, action_elem )
            all_env_shell_file_paths.extend( env_shell_file_paths )
    if all_env_shell_file_paths:
        action_dict[ 'env_shell_file_paths' ] = all_env_shell_file_paths
        action_dict[ 'action_shell_file_paths' ] = env_shell_file_paths
    return action_dict

def get_env_var_values( install_environment ):
    """
    Return a dictionary of values, some of which enable substitution of reserved words for the values.
    The received install_enviroment object has 2 important attributes for reserved word substitution:
    install_environment.tool_shed_repository_install_dir is the root installation directory of the repository
    that contains the tool dependency being installed, and install_environment.install_dir is the root
    installation directory of the tool dependency.
    """
    env_var_dict = {}
    env_var_dict[ 'REPOSITORY_INSTALL_DIR' ] = install_environment.tool_shed_repository_install_dir
    env_var_dict[ 'INSTALL_DIR' ] = install_environment.install_dir
    env_var_dict[ 'system_install' ] = install_environment.install_dir
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
    symlinks = []
    regular_files = []
    for file_name in os.listdir( source_directory ):
        source_file = os.path.join( source_directory, file_name )
        destination_file = os.path.join( destination_directory, file_name )
        files_tuple = ( source_file, destination_file )
        if os.path.islink( source_file ):
            symlinks.append( files_tuple )
        else:
            regular_files.append( files_tuple )
    for source_file, destination_file in symlinks:
        shutil.move( source_file, destination_file )
    for source_file, destination_file in regular_files:
        shutil.move( source_file, destination_file )

def move_file( current_dir, source, destination, rename_to=None ):
    source_path = os.path.abspath( os.path.join( current_dir, source ) )
    source_file = os.path.basename( source_path )
    if rename_to is not None:
        destination_file = rename_to
        destination_directory = os.path.join( destination )
        destination_path = os.path.join( destination_directory, destination_file )
    else:
        destination_directory = os.path.join( destination )
        destination_path = os.path.join( destination_directory, source_file )
    if not os.path.exists( destination_directory ):
        os.makedirs( destination_directory )
    shutil.move( source_path, destination_path )

def parse_package_elem( package_elem, platform_info_dict=None, include_after_install_actions=True ):
    """
    Parse a <package> element within a tool dependency definition and return a list of action tuples.
    This method is called when setting metadata on a repository that includes a tool_dependencies.xml
    file or when installing a repository that includes a tool_dependencies.xml file.  If installing,
    platform_info_dict must be a valid dictionary and include_after_install_actions must be True.
    """
    # The actions_elem_tuples list contains <actions> tag sets (possibly inside of an <actions_group>
    # tag set) to be processed in the order they are defined in the tool_dependencies.xml file.
    actions_elem_tuples = []
    # The tag sets that will go into the actions_elem_list are those that install a compiled binary if
    # the architecture and operating system match its defined attributes.  If compiled binary is not
    # installed, the first <actions> tag set [following those that have the os and architecture attributes]
    # that does not have os or architecture attributes will be processed.  This tag set must contain the
    # recipe for downloading and compiling source.
    actions_elem_list = []
    for elem in package_elem:
        if elem.tag == 'actions':
            # We have an <actions> tag that should not be matched against a specific combination of
            # architecture and operating system.
            in_actions_group = False
            actions_elem_tuples.append( ( in_actions_group, elem ) )
        elif elem.tag == 'actions_group':
            # We have an actions_group element, and its child <actions> elements should therefore be compared
            # with the current operating system
            # and processor architecture.
            in_actions_group = True
            # Record the number of <actions> elements so we can filter out any <action> elements that precede
            # <actions> elements.
            actions_elem_count = len( elem.findall( 'actions' ) )
            # Record the number of <actions> elements that have both architecture and os specified, in order
            # to filter out any platform-independent <actions> elements that come before platform-specific
            # <actions> elements.
            platform_actions_elements = []
            for actions_elem in elem.findall( 'actions' ):
                if actions_elem.get( 'architecture' ) is not None and actions_elem.get( 'os' ) is not None:
                    platform_actions_elements.append( actions_elem )
            platform_actions_element_count = len( platform_actions_elements )
            platform_actions_elements_processed = 0
            actions_elems_processed = 0
            # The tag sets that will go into the after_install_actions list are <action> tags instead of <actions>
            # tags.  These will be processed only if they are at the very end of the <actions_group> tag set (after
            # all <actions> tag sets). See below for details.
            after_install_actions = []
            # Inspect the <actions_group> element and build the actions_elem_list and the after_install_actions list.
            for child_element in elem:
                if child_element.tag == 'actions':
                    actions_elems_processed += 1
                    system = child_element.get( 'os' )
                    architecture = child_element.get( 'architecture' )
                    # Skip <actions> tags that have only one of architecture or os specified, in order for the
                    # count in platform_actions_elements_processed to remain accurate.
                    if ( system and not architecture ) or ( architecture and not system ):
                        log.debug( 'Error: Both architecture and os attributes must be specified in an <actions> tag.' )
                        continue
                    # Since we are inside an <actions_group> tag set, compare it with our current platform information
                    # and filter the <actions> tag sets that don't match. Require both the os and architecture attributes
                    # to be defined in order to find a match.
                    if system and architecture:
                        platform_actions_elements_processed += 1
                        # If either the os or architecture do not match the platform, this <actions> tag will not be
                        # considered a match. Skip it and proceed with checking the next one.
                        if platform_info_dict:
                            if platform_info_dict[ 'os' ] != system or platform_info_dict[ 'architecture' ] != architecture:
                                continue
                        else:
                            # We must not be installing a repository into Galaxy, so determining if we can install a
                            # binary is not necessary.
                            continue
                    else:
                        # <actions> tags without both os and architecture attributes are only allowed to be specified
                        # after platform-specific <actions> tags. If we find a platform-independent <actions> tag before
                        # all platform-specific <actions> tags have been processed.
                        if platform_actions_elements_processed < platform_actions_element_count:
                            debug_msg = 'Error: <actions> tags without os and architecture attributes are only allowed '
                            debug_msg += 'after all <actions> tags with os and architecture attributes have been defined.  '
                            debug_msg += 'Skipping the <actions> tag set with no os or architecture attributes that has '
                            debug_msg += 'been defined between two <actions> tag sets that have these attributes defined.  '
                            log.debug( debug_msg )
                            continue
                    # If we reach this point, it means one of two things: 1) The system and architecture attributes are
                    # not defined in this <actions> tag, or 2) The system and architecture attributes are defined, and
                    # they are an exact match for the current platform. Append the child element to the list of elements
                    # to process.
                    actions_elem_list.append( child_element )
                elif child_element.tag == 'action':
                    # Any <action> tags within an <actions_group> tag set must come after all <actions> tags.
                    if actions_elems_processed == actions_elem_count:
                        # If all <actions> elements have been processed, then this <action> element can be appended to the
                        # list of actions to execute within this group.
                        after_install_actions.append( child_element )
                    else:
                        # If any <actions> elements remain to be processed, then log a message stating that <action>
                        # elements are not allowed to precede any <actions> elements within an <actions_group> tag set.
                        debug_msg = 'Error: <action> tags are only allowed at the end of an <actions_group> tag set after '
                        debug_msg += 'all <actions> tags.  Skipping <%s> element with type %s.' % \
                            ( child_element.tag, child_element.get( 'type', 'unknown' ) )
                        log.debug( debug_msg )
                        continue
            if platform_info_dict is None and not include_after_install_actions:
                # We must be setting metadata on a repository.
                if len( actions_elem_list ) >= 1:
                    actions_elem_tuples.append( ( in_actions_group, actions_elem_list[ 0 ] ) )
                else:
                    # We are processing a recipe that contains only an <actions_group> tag set for installing a binary,
                    # but does not include an additional recipe for installing and compiling from source.
                    actions_elem_tuples.append( ( in_actions_group, [] ) )
            elif platform_info_dict is not None and include_after_install_actions:
                # We must be installing a repository.
                if after_install_actions:
                    actions_elem_list.extend( after_install_actions )
                actions_elem_tuples.append( ( in_actions_group, actions_elem_list ) )
        else:
            # Skip any element that is not <actions> or <actions_group> - this will skip comments, <repository> tags
            # and <readme> tags.
            in_actions_group = False
            continue
    return actions_elem_tuples

def __shellquote( s ):
    """Quote and escape the supplied string for use in shell expressions."""
    return "'" + s.replace( "'", "'\\''" ) + "'"

def url_download( install_dir, downloaded_file_name, download_url, extract=True ):
    file_path = os.path.join( install_dir, downloaded_file_name )
    src = None
    dst = None
    # Set a timer so we don't sit here forever.
    start_time = time.time()
    try:
        src = urllib2.urlopen( download_url )
        dst = open( file_path, 'wb' )
        while True:
            chunk = src.read( suc.CHUNK_SIZE )
            if chunk:
                dst.write( chunk )
            else:
                break
            time_taken = time.time() - start_time
            if time_taken > NO_OUTPUT_TIMEOUT:
                err_msg = 'Downloading from URL %s took longer than the defined timeout period of %.1f seconds.' % \
                    ( str( download_url ), NO_OUTPUT_TIMEOUT )
                raise Exception( err_msg )
    except Exception, e:
        err_msg = err_msg = 'Error downloading from URL\n%s:\n%s' % ( str( download_url ), str( e ) )
        raise Exception( err_msg )
    finally:
        if src:
            src.close()
        if dst:
            dst.close()
    if extract:
        if istar( file_path ) or ( iszip( file_path ) and not isjar( file_path ) ):
            archive = CompressedFile( file_path )
            extraction_path = archive.extract( install_dir )
        else:
            extraction_path = os.path.abspath( install_dir )
    else:
        extraction_path = os.path.abspath( install_dir )
    return extraction_path

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
