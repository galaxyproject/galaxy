import logging
import os
import sys
import subprocess
import tempfile
from string import Template
import common_util
import fabric_util
import tool_shed.util.shed_util_common as suc
import tool_shed.util.common_util as cu
from tool_shed.util import encoding_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import xml_util
from galaxy.model.orm import and_
from galaxy.web import url_for

log = logging.getLogger( __name__ )

def clean_tool_shed_url( base_url ):
    protocol, base = base_url.split( '://' )
    return base.rstrip( '/' )

def create_temporary_tool_dependencies_config( app, tool_shed_url, name, owner, changeset_revision ):
    """Make a call to the tool shed to get the required repository's tool_dependencies.xml file."""
    url = url_join( tool_shed_url,
                    'repository/get_tool_dependencies_config_contents?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision ) )
    text = cu.tool_shed_get( app, tool_shed_url, url )
    if text:
        # Write the contents to a temporary file on disk so it can be reloaded and parsed.
        fh = tempfile.NamedTemporaryFile( 'wb' )
        tmp_filename = fh.name
        fh.close()
        fh = open( tmp_filename, 'wb' )
        fh.write( text )
        fh.close()
        return tmp_filename
    else:
        message = "Unable to retrieve required tool_dependencies.xml file from the tool shed for revision "
        message += "%s of installed repository %s owned by %s." % ( str( changeset_revision ), str( name ), str( owner ) )
        raise Exception( message )
        return None

def get_absolute_path_to_file_in_repository( repo_files_dir, file_name ):
    """Return the absolute path to a specified disk file contained in a repository."""
    stripped_file_name = strip_path( file_name )
    file_path = None
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == stripped_file_name:
                    return os.path.abspath( os.path.join( root, name ) )
    return file_path

def get_tool_shed_repository_by_tool_shed_name_owner_changeset_revision( app, tool_shed_url, name, owner, changeset_revision ):
    sa_session = app.model.context.current
    tool_shed = clean_tool_shed_url( tool_shed_url )
    tool_shed_repository =  sa_session.query( app.model.ToolShedRepository ) \
                                      .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                                     app.model.ToolShedRepository.table.c.name == name,
                                                     app.model.ToolShedRepository.table.c.owner == owner,
                                                     app.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                                      .first()
    if tool_shed_repository:
        return tool_shed_repository
    # The tool_shed_repository must have been updated to a newer changeset revision than the one defined in the repository_dependencies.xml file,
    # so call the tool shed to get all appropriate newer changeset revisions.
    text = get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision )
    if text:
        changeset_revisions = listify( text )
        for changeset_revision in changeset_revisions:
            tool_shed_repository = sa_session.query( app.model.ToolShedRepository ) \
                                             .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                                            app.model.ToolShedRepository.table.c.name == name,
                                                            app.model.ToolShedRepository.table.c.owner == owner,
                                                            app.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                                             .first()
            if tool_shed_repository:
                return tool_shed_repository
    return None

def get_tool_dependency_install_dir( app, repository_name, repository_owner, repository_changeset_revision, tool_dependency_type, tool_dependency_name,
                                     tool_dependency_version ):
    if tool_dependency_type == 'package':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              tool_dependency_name,
                                              tool_dependency_version,
                                              repository_owner,
                                              repository_name,
                                              repository_changeset_revision ) )
    if tool_dependency_type == 'set_environment':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              'environment_settings',
                                              tool_dependency_name,
                                              repository_owner,
                                              repository_name,
                                              repository_changeset_revision ) )

def get_tool_shed_repository_install_dir( app, tool_shed_repository ):
    return os.path.abspath( tool_shed_repository.repo_files_directory( app ) )

def get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Get all appropriate newer changeset revisions for the repository defined by 
    the received tool_shed_url / name / owner combination.
    """
    url = suc.url_join( tool_shed_url,
                        'repository/updated_changeset_revisions?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision ) )
    text = cu.tool_shed_get( app, tool_shed_url, url )
    return text

def handle_set_environment_entry_for_package( app, install_dir, tool_shed_repository, package_name, package_version, elem, required_repository ):
    """
    Populate a list of actions for creating an env.sh file for a dependent repository.  The received elem is the <package> tag set associated
    with the tool-dependencies.xml file for one of the received tool_shed_repository's repository dependency.
    """
    action_dict = {}
    actions = []
    for package_elem in elem:
        if package_elem.tag == 'install':
            # Create the tool_dependency record in the database.
            tool_dependency = tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                     tool_shed_repository=tool_shed_repository,
                                                                                     name=package_name,
                                                                                     version=package_version,
                                                                                     type='package',
                                                                                     status=app.model.ToolDependency.installation_status.INSTALLING,
                                                                                     set_status=True )
            # Get the installation method version from a tag like: <install version="1.0">
            package_install_version = package_elem.get( 'version', '1.0' )
            if package_install_version == '1.0':
                # Since the required tool dependency is installed for a repository dependency, we first need to inspect the <actions> tag set to find
                # the <action type="set_environment"> tag.
                env_var_dicts = []
                for actions_elem in package_elem:
                    for action_elem in actions_elem:
                        action_type = action_elem.get( 'type', 'shell_command' )
                        if action_type == 'set_environment':
                            # <action type="set_environment">
                            #     <environment_variable name="PYTHONPATH" action="append_to">$INSTALL_DIR/lib/python</environment_variable>
                            #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
                            # </action>
                            for env_elem in action_elem:
                                if env_elem.tag == 'environment_variable':
                                    env_var_dict = common_util.create_env_var_dict( env_elem, tool_dependency_install_dir=install_dir )
                                    if env_var_dict:
                                        if env_var_dict not in env_var_dicts:
                                            env_var_dicts.append( env_var_dict )
                        elif action_type == 'setup_virtualenv':
                            # Add the virtualenv's site-packages to PYTHONPATH and bin to PATH.  This is a bit hackish.
                            site_packages_command = "%s -c 'import os, sys; print os.path.join(sys.prefix, \"lib\", \"python\" + sys.version[:3], \"site-packages\")'" % os.path.join( install_dir, "venv", "bin", "python" )
                            output = fabric_util.handle_command( app, tool_dependency, install_dir, site_packages_command, return_output=True )
                            if output.return_code:
                                log.error( 'Dependency includes a setup_virtualenv action but venv python is broken:', output.stderr )
                            elif not os.path.exists( output.stdout ):
                                log.error( "virtualenv's site-packages directory '%s' does not exist", output.stdout )
                            else:
                                env_var_dicts.append( dict( name="PYTHONPATH", action="prepend_to", value=output.stdout ) )
                                env_var_dicts.append( dict( name="PATH", action="prepend_to", value=os.path.join( install_dir, 'venv', 'bin' ) ) )
                if env_var_dicts:
                    if required_repository.status in [ app.model.ToolShedRepository.installation_status.INSTALLED,
                                                       app.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                        # Handle the case where we have an installed required repository due to the prior_installation_required = True
                        # setting in the received tool_shed_repository's tool_dependencies.xml file and the required repository's
                        # tool_dependencies.xml file may include the use of the $ENV[] variable inheritance feature.  To handle this,
                        # we will replace the current "value" entries in each env_var_dict with the actual path taken from the env.sh
                        # file generated for the installed required repository.  Each env_var_dict currently looks something like this: 
                        # {'action': 'append_to', 'name': 'LD_LIBRARY_PATH', 'value': '$BOOST_ROOT_DIR/lib/'}
                        # We'll read the contents of the received required_repository's env.sh file and replace the 'value' entry of each env_var_dict
                        # with the associated value in the env.sh file.
                        new_env_var_dicts = []
                        env_sh_file_dir = get_tool_dependency_install_dir( app=app,
                                                                           repository_name=required_repository.name,
                                                                           repository_owner=required_repository.owner,
                                                                           repository_changeset_revision=required_repository.installed_changeset_revision,
                                                                           tool_dependency_type='package',
                                                                           tool_dependency_name=package_name,
                                                                           tool_dependency_version=package_version )
                        env_sh_file_path = os.path.join( env_sh_file_dir, 'env.sh' )
                        for i, line in enumerate( open( env_sh_file_path, 'r' ) ):
                            env_var_dict = env_var_dicts[ i ]
                            action = env_var_dict.get( 'action', None )
                            name = env_var_dict.get( 'name', None )
                            value = env_var_dict.get( 'value', None )
                            if action and name and value:
                                new_value = parse_env_shell_entry( action, name, value, line )
                                env_var_dict[ 'value' ] = new_value
                            new_env_var_dicts.append( env_var_dict )
                        action_dict[ 'environment_variable' ] = new_env_var_dicts
                    else:
                        action_dict[ 'environment_variable' ] = env_var_dicts
                    actions.append( ( 'set_environment', action_dict ) )
                    return tool_dependency, actions
            else:
                raise NotImplementedError( 'Only install version 1.0 is currently supported (i.e., change your tag to be <install version="1.0">).' )
    return None, actions

def install_and_build_package_via_fabric( app, tool_dependency, actions_dict ):
    sa_session = app.model.context.current
    try:
        # There is currently only one fabric method.
        fabric_util.install_and_build_package( app, tool_dependency, actions_dict )
    except Exception, e:
        log.exception( 'Error installing tool dependency %s version %s.', str( tool_dependency.name ), str( tool_dependency.version ) )
        tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
        tool_dependency.error_message = '%s\n%s' % ( common_util.format_traceback(), str( e ) ) 
        sa_session.add( tool_dependency )
        sa_session.flush()
    if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
        tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
        sa_session.add( tool_dependency )
        sa_session.flush()

def install_package( app, elem, tool_shed_repository, tool_dependencies=None ):
    # The value of tool_dependencies is a partial or full list of ToolDependency records associated with the tool_shed_repository.
    sa_session = app.model.context.current
    tool_dependency = None
    # The value of package_name should match the value of the "package" type in the tool config's <requirements> tag set, but it's not required.
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if tool_dependencies and package_name and package_version:
        for package_elem in elem:
            if package_elem.tag == 'repository':
                # We have a complex repository dependency definition.
                tool_shed = package_elem.attrib[ 'toolshed' ]
                required_repository_name = package_elem.attrib[ 'name' ]
                required_repository_owner = package_elem.attrib[ 'owner' ]
                default_required_repository_changeset_revision = package_elem.attrib[ 'changeset_revision' ]
                required_repository = get_tool_shed_repository_by_tool_shed_name_owner_changeset_revision( app,
                                                                                                           tool_shed,
                                                                                                           required_repository_name,
                                                                                                           required_repository_owner,
                                                                                                           default_required_repository_changeset_revision )
                tmp_filename = None
                if required_repository:
                    required_repository_changeset_revision = required_repository.installed_changeset_revision
                    # Define the installation directory for the required tool dependency package in the required repository.
                    required_repository_package_install_dir = \
                        get_tool_dependency_install_dir( app=app,
                                                         repository_name=required_repository_name,
                                                         repository_owner=required_repository_owner,
                                                         repository_changeset_revision=required_repository_changeset_revision,
                                                         tool_dependency_type='package',
                                                         tool_dependency_name=package_name,
                                                         tool_dependency_version=package_version )
                    # Define the this dependent repository's tool dependency installation directory that will contain the env.sh file with a path to the
                    # required repository's installed tool dependency package.
                    dependent_install_dir = get_tool_dependency_install_dir( app=app,
                                                                             repository_name=tool_shed_repository.name,
                                                                             repository_owner=tool_shed_repository.owner,
                                                                             repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                             tool_dependency_type='package',
                                                                             tool_dependency_name=package_name,
                                                                             tool_dependency_version=package_version )
                    # Set this dependent repository's tool dependency env.sh file with a path to the required repository's installed tool dependency package.
                    # We can get everything we need from the discovered installed required_repository.
                    if required_repository.status in [ app.model.ToolShedRepository.installation_status.DEACTIVATED,
                                                       app.model.ToolShedRepository.installation_status.INSTALLED ]:                        
                        if not os.path.exists( required_repository_package_install_dir ):
                            print 'Missing required tool dependency directory %s' % str( required_repository_package_install_dir )
                        repo_files_dir = required_repository.repo_files_directory( app )
                        tool_dependencies_config = get_absolute_path_to_file_in_repository( repo_files_dir, 'tool_dependencies.xml' )
                        if tool_dependencies_config:
                            config_to_use = tool_dependencies_config
                        else:
                            message = "Unable to locate required tool_dependencies.xml file for revision %s of installed repository %s owned by %s." % \
                                ( str( required_repository.changeset_revision ), str( required_repository.name ), str( required_repository.owner ) )
                            raise Exception( message )
                    else:
                        # Make a call to the tool shed to get the changeset revision to which the current value of required_repository_changeset_revision
                        # should be updated if it's not current.
                        text = get_updated_changeset_revisions_from_tool_shed( app=app,
                                                                               tool_shed_url=tool_shed,
                                                                               name=required_repository_name,
                                                                               owner=required_repository_owner,
                                                                               changeset_revision=required_repository_changeset_revision )
                        if text:
                            updated_changeset_revisions = listify( text )
                            # The list of changeset revisions is in reverse order, so the newest will be first.
                            required_repository_changeset_revision = updated_changeset_revisions[ 0 ]
                        # Make a call to the tool shed to get the required repository's tool_dependencies.xml file.
                        tmp_filename = create_temporary_tool_dependencies_config( app,
                                                                                  tool_shed,
                                                                                  required_repository_name,
                                                                                  required_repository_owner,
                                                                                  required_repository_changeset_revision )
                        config_to_use = tmp_filename
                    tool_dependency, actions_dict = populate_actions_dict( app=app,
                                                                           dependent_install_dir=dependent_install_dir,
                                                                           required_install_dir=required_repository_package_install_dir,
                                                                           tool_shed_repository=tool_shed_repository,
                                                                           required_repository=required_repository,
                                                                           package_name=package_name,
                                                                           package_version=package_version,
                                                                           tool_dependencies_config=config_to_use )
                    if tmp_filename:
                        try:
                            os.remove( tmp_filename )
                        except:
                            pass
                    # Install and build the package via fabric.
                    install_and_build_package_via_fabric( app, tool_dependency, actions_dict )
                else:
                    message = "Unable to locate required tool shed repository named %s owned by %s with revision %s." % \
                        ( str( required_repository_name ), str( required_repository_owner ), str( default_required_repository_changeset_revision ) )
                    raise Exception( message )
            elif package_elem.tag == 'install':
                # <install version="1.0">
                # Get the installation directory for tool dependencies that will be installed for the received tool_shed_repository.
                install_dir = get_tool_dependency_install_dir( app=app,
                                                               repository_name=tool_shed_repository.name,
                                                               repository_owner=tool_shed_repository.owner,
                                                               repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                               tool_dependency_type='package',
                                                               tool_dependency_name=package_name,
                                                               tool_dependency_version=package_version )
                if os.path.exists( install_dir ):
                    print '\nSkipping installation of tool dependency', package_name, 'version', package_version, 'since it is installed in', install_dir, '\n'
                    tool_dependency = tool_dependency_util.get_tool_dependency_by_name_version_type_repository( app,
                                                                                                                tool_shed_repository,
                                                                                                                package_name,
                                                                                                                package_version,
                                                                                                                'package' )
                    tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
                    sa_session.add( tool_dependency )
                    sa_session.flush()
                else:
                    package_install_version = package_elem.get( 'version', '1.0' )
                    tool_dependency = tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                             tool_shed_repository=tool_shed_repository,
                                                                                             name=package_name,
                                                                                             version=package_version,
                                                                                             type='package',
                                                                                             status=app.model.ToolDependency.installation_status.INSTALLING,
                                                                                             set_status=True )
                    if package_install_version == '1.0':
                        # Handle tool dependency installation using a fabric method included in the Galaxy framework.
                        for actions_elem in package_elem:
                            install_via_fabric( app, tool_dependency, actions_elem, install_dir, package_name=package_name )
                            sa_session.refresh( tool_dependency )
                            if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
                                print package_name, 'version', package_version, 'installed in', install_dir
                    else:
                        raise NotImplementedError( 'Only install version 1.0 is currently supported (i.e., change your tag to be <install version="1.0">).' )
            elif package_elem.tag == 'readme':
                # Nothing to be done.
                continue
            #elif package_elem.tag == 'proprietary_fabfile':
            #    # TODO: This is not yet supported or functionally correct...
            #    # Handle tool dependency installation where the repository includes one or more proprietary fabric scripts.
            #    if not fabric_version_checked:
            #        check_fabric_version()
            #        fabric_version_checked = True
            #    fabfile_name = package_elem.get( 'name', None )
            #    proprietary_fabfile_path = os.path.abspath( os.path.join( os.path.split( tool_dependencies_config )[ 0 ], fabfile_name ) )
            #    print 'Installing tool dependencies via fabric script ', proprietary_fabfile_path
    return tool_dependency

def install_via_fabric( app, tool_dependency, actions_elem, install_dir, package_name=None, proprietary_fabfile_path=None, **kwd ):
    """Parse a tool_dependency.xml file's <actions> tag set to gather information for the installation via fabric."""
    sa_session = app.model.context.current

    def evaluate_template( text ):
        """ Substitute variables defined in XML blocks obtained loaded from dependencies file. """
        # # Added for compatibility with CloudBioLinux.
        # TODO: Add tool_version substitution for compat with CloudBioLinux.
        substitutions = { "INSTALL_DIR" : install_dir,
                          "system_install" : install_dir }
        return Template( text ).safe_substitute( substitutions )

    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    actions_dict = dict( install_dir=install_dir )
    if package_name:
        actions_dict[ 'package_name' ] = package_name
    actions = []
    all_env_shell_file_paths = []
    env_var_dicts = []
    # Make sure to skip all comments, since they are now included in the XML tree.
    for action_elem in actions_elem.findall( 'action' ):
        action_dict = {}
        action_type = action_elem.get( 'type', 'shell_command' )
        if action_type == 'shell_command':
            # <action type="shell_command">make</action>
            action_elem_text = evaluate_template( action_elem.text )
            if action_elem_text:
                action_dict[ 'command' ] = action_elem_text
            else:
                continue
        elif action_type == 'download_by_url':
            # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
            if action_elem.text:
                action_dict[ 'url' ] = action_elem.text
                if 'target_filename' in action_elem.attrib:
                    action_dict[ 'target_filename' ] = action_elem.attrib[ 'target_filename' ]
            else:
                continue
        elif action_type == 'download_file':
            # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
            if action_elem.text:
                action_dict[ 'url' ] = action_elem.text
                action_dict[ 'target_filename' ] = action_elem.attrib.get( 'target_filename', None )
            else:
                continue
        elif action_type == 'make_directory':
            # <action type="make_directory">$INSTALL_DIR/lib/python</action>
            if action_elem.text:
                action_dict[ 'full_path' ] = evaluate_template( action_elem.text )
            else:
                continue
        elif action_type in [ 'move_directory_files', 'move_file' ]:
            # <action type="move_file">
            #     <source>misc/some_file</source>
            #     <destination>$INSTALL_DIR/bin</destination>
            # </action>
            # <action type="move_directory_files">
            #     <source_directory>bin</source_directory>
            #     <destination_directory>$INSTALL_DIR/bin</destination_directory>
            # </action>
            for move_elem in action_elem:
                move_elem_text = evaluate_template( move_elem.text )
                if move_elem_text:
                    action_dict[ move_elem.tag ] = move_elem_text
        elif action_type == 'set_environment':
            # <action type="set_environment">
            #     <environment_variable name="PYTHONPATH" action="append_to">$INSTALL_DIR/lib/python</environment_variable>
            #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
            # </action>
            for env_elem in action_elem:
                if env_elem.tag == 'environment_variable':
                    env_var_dict = common_util.create_env_var_dict( env_elem, tool_dependency_install_dir=install_dir )
                    if env_var_dict:
                        env_var_dicts.append( env_var_dict )
            if env_var_dicts:
                action_dict[ env_elem.tag ] = env_var_dicts
            else:
                continue
        elif action_type == 'set_environment_for_install':
            # <action type="set_environment_for_install">
            #    <repository toolshed="http://localhost:9009/" name="package_numpy_1_7" owner="test" changeset_revision="c84c6a8be056">
            #        <package name="numpy" version="1.7.1" />
            #    </repository>
            # </action>
            # This action type allows for defining an environment that will properly compile a tool dependency.  Currently, tag set definitions like
            # that above are supported, but in the future other approaches to setting environment variables or other environment attributes can be 
            # supported.  The above tag set will result in the installed and compiled numpy version 1.7.1 binary to be used when compiling the current
            # tool dependency package.  See the package_matplotlib_1_2 repository in the test tool shed for a real-world example.
            for env_elem in action_elem:
                if env_elem.tag == 'repository':
                    env_shell_file_paths = common_util.get_env_shell_file_paths( app, env_elem )
                    if env_shell_file_paths:
                        all_env_shell_file_paths.extend( env_shell_file_paths )
            if all_env_shell_file_paths:
                action_dict[ 'env_shell_file_paths' ] = all_env_shell_file_paths
            else:
                continue
        elif action_type == 'setup_virtualenv':
            # <action type="setup_virtualenv" />
            ## Install requirements from file requirements.txt of downloaded bundle - or -
            # <action type="setup_virtualenv">tools/requirements.txt</action>
            ## Install requirements from specified file from downloaded bundle -or -
            # <action type="setup_virtualenv">pyyaml==3.2.0
            # lxml==2.3.0</action>
            ## Manually specify contents of requirements.txt file to create dynamically.
            action_dict[ 'requirements' ] = evaluate_template( action_elem.text or 'requirements.txt' )
        else:
            log.debug( "Unsupported action type '%s'. Not proceeding." % str( action_type ) )
            raise Exception( "Unsupported action type '%s' in tool dependency definition." % str( action_type ) )
        action_tuple = ( action_type, action_dict )
        if action_type == 'set_environment':
            if action_tuple not in actions:
                actions.append( action_tuple )
        else:
            actions.append( action_tuple )
    if actions:
        actions_dict[ 'actions' ] = actions
    if proprietary_fabfile_path:
        # TODO: this is not yet supported or functional, but when it is handle it using the fabric api.
        # run_proprietary_fabric_method( app, elem, proprietary_fabfile_path, install_dir, package_name=package_name )
        raise Exception( 'Tool dependency installation using proprietary fabric scripts is not yet supported.' )
    else:
        install_and_build_package_via_fabric( app, tool_dependency, actions_dict )

def listify( item ):
    """
    Make a single item a single item list, or return a list if passed a
    list.  Passing a None returns an empty list.
    """
    if not item:
        return []
    elif isinstance( item, list ):
        return item
    elif isinstance( item, basestring ) and item.count( ',' ):
        return item.split( ',' )
    else:
        return [ item ]

def parse_env_shell_entry( action, name, value, line ):
    new_value = value
    var_name = '$%s' % name
    tmp_value = line.split( '=' )[ 1 ]
    if action == 'prepend_to':
        # PATH=/test/package_rdkit_2012_12/62ebd7bb637a/rdkit/bin:$PATH; export PATH
        new_value = tmp_value.split( ':%s' % var_name )[ 0 ]
    elif action == 'set_to':
        # RDBASE=test/package_rdkit_2012_12/62ebd7bb637a/rdkit; export RDBASE
        new_value = tmp_value.split( ';' )[ 0 ]
    elif action == 'append_to':
        # LD_LIBRARY_PATH=$LD_LIBRARY_PATH:test/package_rdkit_2012_12/62ebd7bb637a/rdkit/lib/; export LD_LIBRARY_PATH
        new_value = tmp_value.split( ':' )[ 1 ]
        new_value = new_value.split( ';' )[ 0 ]
    return new_value

        
def populate_actions_dict( app, dependent_install_dir, required_install_dir, tool_shed_repository, required_repository, package_name, package_version, tool_dependencies_config ):
    """
    Populate an actions dictionary that can be sent to fabric_util.install_and_build_package.  This method handles the scenario where a tool_dependencies.xml
    file defines a complex repository dependency.  In this case, the tool dependency package will be installed in a separate repository and the tool dependency
    defined for the dependent repository will use an environment_variable setting defined in it's env.sh file to locate the required package.  This method
    basically does what the install_via_fabric method does, but restricts it's activity to the <action type="set_environment"> tag set within the required
    repository's tool_dependencies.xml file.
    """
    sa_session = app.model.context.current
    if not os.path.exists( dependent_install_dir ):
        os.makedirs( dependent_install_dir )
    actions_dict = dict( install_dir=dependent_install_dir )
    if package_name:
        actions_dict[ 'package_name' ] = package_name
    tool_dependency = None
    action_dict = {}
    if tool_dependencies_config:
        required_td_tree, error_message = xml_util.parse_xml( tool_dependencies_config )
        if required_td_tree:
            required_td_root = required_td_tree.getroot()
            for required_td_elem in required_td_root:
                # Find the appropriate package name and version.
                if required_td_elem.tag == 'package':
                    # <package name="bwa" version="0.5.9">
                    required_td_package_name = required_td_elem.get( 'name', None )
                    required_td_package_version = required_td_elem.get( 'version', None )
                    if required_td_package_name==package_name and required_td_package_version==package_version:
                        tool_dependency, actions = handle_set_environment_entry_for_package( app=app,
                                                                                             install_dir=required_install_dir,
                                                                                             tool_shed_repository=tool_shed_repository,
                                                                                             package_name=package_name,
                                                                                             package_version=package_version,
                                                                                             elem=required_td_elem,
                                                                                             required_repository=required_repository )
                        if actions:
                            actions_dict[ 'actions' ] = actions
                        break
    return tool_dependency, actions_dict

def run_proprietary_fabric_method( app, elem, proprietary_fabfile_path, install_dir, package_name=None, **kwd ):
    """
    TODO: Handle this using the fabric api.
    Parse a tool_dependency.xml file's fabfile <method> tag set to build the method parameters and execute the method.
    """
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    # Default value for env_dependency_path.
    env_dependency_path = install_dir
    method_name = elem.get( 'name', None )
    params_str = ''
    actions = []
    for param_elem in elem:
        param_name = param_elem.get( 'name' )
        if param_name:
            if param_name == 'actions':
                for action_elem in param_elem:
                    actions.append( action_elem.text.replace( '$INSTALL_DIR', install_dir ) )
                if actions:
                    params_str += 'actions=%s,' % encoding_util.tool_shed_encode( encoding_util.encoding_sep.join( actions ) )
            else:
                if param_elem.text:
                    param_value = encoding_util.tool_shed_encode( param_elem.text )
                    params_str += '%s=%s,' % ( param_name, param_value )
    if package_name:
        params_str += 'package_name=%s' % package_name
    else:
        params_str = params_str.rstrip( ',' )
    try:
        cmd = 'fab -f %s %s:%s' % ( proprietary_fabfile_path, method_name, params_str )
        returncode, message = run_subprocess( app, cmd )
    except Exception, e:
        return "Exception executing fabric script %s: %s.  " % ( str( proprietary_fabfile_path ), str( e ) )
    if returncode:
        return message    
    handle_environment_settings( app, tool_dependency, install_dir, cmd )

def run_subprocess( app, cmd ):
    env = os.environ
    PYTHONPATH = env.get( 'PYTHONPATH', '' )
    if PYTHONPATH:
        env[ 'PYTHONPATH' ] = '%s:%s' % ( os.path.abspath( os.path.join( app.config.root, 'lib' ) ), PYTHONPATH )
    else:
        env[ 'PYTHONPATH' ] = os.path.abspath( os.path.join( app.config.root, 'lib' ) )
    message = ''
    tmp_name = tempfile.NamedTemporaryFile().name
    tmp_stderr = open( tmp_name, 'wb' )
    proc = subprocess.Popen( cmd, shell=True, env=env, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    tmp_stderr.close()
    if returncode:
        tmp_stderr = open( tmp_name, 'rb' )
        message = '%s\n' % str( tmp_stderr.read() )
        tmp_stderr.close()
    try:
        os.remove( tmp_name )
    except:
        pass
    return returncode, message

def set_environment( app, elem, tool_shed_repository ):
    """
    Create a ToolDependency to set an environment variable.  This is different from the process used to set an environment variable that is associated
    with a package.  An example entry in a tool_dependencies.xml file is::

        <set_environment version="1.0">
            <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
        </set_environment>
    """
    # TODO: Add support for a repository dependency definition within this tool dependency type's tag set.  This should look something like
    # the following.  See the implementation of support for this in the tool dependency package type's method above.
    # <set_environment version="1.0">
    #    <repository toolshed="<tool shed>" name="<repository name>" owner="<repository owner>" changeset_revision="<changeset revision>" />
    # </set_environment>
    sa_session = app.model.context.current
    tool_dependency = None
    env_var_version = elem.get( 'version', '1.0' )
    for env_var_elem in elem:
        # The value of env_var_name must match the text value of at least 1 <requirement> tag in the tool config's <requirements> tag set whose
        # "type" attribute is "set_environment" (e.g., <requirement type="set_environment">R_SCRIPT_PATH</requirement>).
        env_var_name = env_var_elem.get( 'name', None )
        env_var_action = env_var_elem.get( 'action', None )
        if env_var_name and env_var_action:
            install_dir = get_tool_dependency_install_dir( app=app,
                                                           repository_name=tool_shed_repository.name,
                                                           repository_owner=tool_shed_repository.owner,
                                                           repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                           tool_dependency_type='set_environment',
                                                           tool_dependency_name=env_var_name,
                                                           tool_dependency_version=None )
            tool_shed_repository_install_dir = get_tool_shed_repository_install_dir( app, tool_shed_repository )
            env_var_dict = common_util.create_env_var_dict( env_var_elem, tool_shed_repository_install_dir=tool_shed_repository_install_dir )
            if env_var_dict:
                if not os.path.exists( install_dir ):
                    os.makedirs( install_dir )
                tool_dependency = tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                         tool_shed_repository=tool_shed_repository,
                                                                                         name=env_var_name,
                                                                                         version=None,
                                                                                         type='set_environment',
                                                                                         status=app.model.ToolDependency.installation_status.INSTALLING,
                                                                                         set_status=True )
                cmd = common_util.create_or_update_env_shell_file( install_dir, env_var_dict )
                if env_var_version == '1.0':
                    # Handle setting environment variables using a fabric method.
                    fabric_util.handle_command( app, tool_dependency, install_dir, cmd )
                    sa_session.refresh( tool_dependency )
                    if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
                        tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
                        sa_session.add( tool_dependency )
                        sa_session.flush()
                        print 'Environment variable ', env_var_name, 'set in', install_dir
                else:
                    raise NotImplementedError( 'Only set_environment version 1.0 is currently supported (i.e., change your tag to be <set_environment version="1.0">).' )

def strip_path( fpath ):
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def url_join( *args ):
    parts = []
    for arg in args:
        parts.append( arg.strip( '/' ) )
    return '/'.join( parts )