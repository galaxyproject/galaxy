import logging
import os
import sys
from tool_shed.util import common_util
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )


class EnvManager( object ):

    def __init__( self, app ):
        self.app = app

    def create_env_var_dict( self, elem, install_environment ):
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
    
    def get_env_shell_file_path( self, installation_directory ):
        env_shell_file_name = 'env.sh'
        default_location = os.path.abspath( os.path.join( installation_directory, env_shell_file_name ) )
        if os.path.exists( default_location ):
            return default_location
        for root, dirs, files in os.walk( installation_directory ):
            for name in files:
                if name == env_shell_file_name:
                    return os.path.abspath( os.path.join( root, name ) )
        return None
    
    def get_env_shell_file_paths( self, elem ):
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
            repository = suc.get_repository_for_dependency_relationship( self.app,
                                                                         toolshed,
                                                                         repository_name,
                                                                         repository_owner,
                                                                         changeset_revision )
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
                            installation_directory = tool_dependency.installation_directory( self.app )
                            env_shell_file_path = self.get_env_shell_file_path( installation_directory )
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
    
    def get_env_shell_file_paths_from_setup_environment_elem( self, all_env_shell_file_paths, elem, action_dict ):
        """
        Parse an XML tag set to discover all child repository dependency tags and define the path to an env.sh file associated
        with the repository (this requires the repository dependency to be in an installed state).  The received action_dict
        will be updated with these discovered paths and returned to the caller.  This method handles tool dependency definition
        tag sets <setup_r_environment>, <setup_ruby_environment>, <setup_python_environment> and <setup_perl_environment>.
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
                env_shell_file_paths = self.get_env_shell_file_paths( action_elem )
                all_env_shell_file_paths.extend( env_shell_file_paths )
        if all_env_shell_file_paths:
            action_dict[ 'env_shell_file_paths' ] = all_env_shell_file_paths
            action_dict[ 'action_shell_file_paths' ] = env_shell_file_paths
        return action_dict
