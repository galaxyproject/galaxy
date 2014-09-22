#!/usr/bin/env python
"""
This script cannot be run directly, because it needs to have test/functional/test_toolbox.py in sys.argv in
order to run functional tests on repository tools after installation. The install_and_test_tool_shed_repositories.sh
will execute this script with the appropriate parameters.
"""
import os
import sys
# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
sys.path.append( cwd )
new_path = [ os.path.join( cwd, "scripts" ),
             os.path.join( cwd, "lib" ),
             os.path.join( cwd, 'test' ),
             os.path.join( cwd, 'scripts', 'api' ) ]
new_path.extend( sys.path )
sys.path = new_path

from galaxy import eggs
eggs.require( "nose" )
eggs.require( "Paste" )
eggs.require( 'mercurial' )
# This should not be required, but it is under certain conditions thanks to this bug:
# http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import httplib
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
import install_and_test_tool_shed_repositories.functional.test_install_repositories as test_install_repositories
import logging
import nose
import random
import re
import shutil
import socket
import tempfile
import time
import threading

import install_and_test_tool_shed_repositories.base.util as install_and_test_base_util

from base.tool_shed_util import parse_tool_panel_config

from galaxy.app import UniverseApplication
from galaxy.util.json import loads
from galaxy.util import asbool
from galaxy.util import unicodify
from galaxy.web import buildapp
from functional_tests import generate_config_file
from nose.plugins import Plugin
from paste import httpserver

from functional import database_contexts

log = logging.getLogger( 'install_and_test_repositories_with_tools' )

assert sys.version_info[ :2 ] >= ( 2, 6 )
test_home_directory = os.path.join( cwd, 'test', 'install_and_test_tool_shed_repositories', 'repositories_with_tools' )

# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the database, new repositories, etc.
galaxy_test_tmp_dir = os.path.join( test_home_directory, 'tmp' )
# File containing information about problematic repositories to exclude from test runs.
exclude_list_file = os.path.abspath( os.path.join( test_home_directory, 'exclude.xml' ) )
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"
os.environ[ 'GALAXY_INSTALL_TEST_TMP_DIR' ] = galaxy_test_tmp_dir

# Use separate databases for Galaxy and tool shed install info by default,
# set GALAXY_TEST_INSTALL_DB_MERGED to True to revert to merged databases
# behavior.
default_install_db_merged = False

# This script can be run in such a way that no Tool Shed database records should be changed.
if '-info_only' in sys.argv or 'GALAXY_INSTALL_TEST_INFO_ONLY' in os.environ:
    can_update_tool_shed = False
else:
    can_update_tool_shed = True

test_framework = install_and_test_base_util.REPOSITORIES_WITH_TOOLS
    
def get_failed_test_dicts( test_result, from_tool_test=True ):
    """Extract any useful data from the test_result.failures and test_result.errors attributes."""
    failed_test_dicts = []
    for failure in test_result.failures + test_result.errors:
        # Record the twill test identifier and information about the tool so the repository owner
        # can discover which test is failing.
        test_id = str( failure[ 0 ] )
        if not from_tool_test:
            tool_id = None
            tool_version = None
        else:
            tool_id, tool_version = get_tool_info_from_test_id( test_id )
        test_status_dict = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
        log_output = failure[ 1 ].replace( '\\n', '\n' )
        # Remove debug output.
        log_output = re.sub( r'control \d+:.+', r'', log_output )
        log_output = re.sub( r'\n+', r'\n', log_output )
        appending_to = 'output'
        tmp_output = {}
        output = {}
        # Iterate through the functional test output and extract only the important data. Captured
        # logging and stdout are not recorded.
        for line in log_output.split( '\n' ):
            if line.startswith( 'Traceback' ):
                appending_to = 'traceback'
            elif '>> end captured' in line or '>> end tool' in line:
                continue
            elif 'request returned None from get_history' in line:
                continue
            elif '>> begin captured logging <<' in line:
                appending_to = 'logging'
                continue
            elif '>> begin captured stdout <<' in line:
                appending_to = 'stdout'
                continue
            elif '>> begin captured stderr <<' in line or '>> begin tool stderr <<' in line:
                appending_to = 'stderr'
                continue
            if appending_to in tmp_output:
                tmp_output[ appending_to ].append( line )
            else:
                tmp_output[ appending_to ] = [ line ]
        for output_type in [ 'stderr', 'traceback' ]:
            if output_type in tmp_output:
                test_status_dict[ output_type ] = '\n'.join( tmp_output[ output_type ] )
        failed_test_dicts.append( test_status_dict )
    return failed_test_dicts

def get_tool_info_from_test_id( test_id ):
    """
    Test IDs come in the form test_tool_number
    (functional.test_toolbox.TestForTool_toolshed_url/repos/owner/repository_name/tool_id/tool_version)
    We want the tool ID and tool version.
    """
    parts = test_id.replace( ')', '' ).split( '/' )
    tool_version = parts[ -1 ]
    tool_id = parts[ -2 ]
    return tool_id, tool_version

def install_and_test_repositories( app, galaxy_shed_tools_dict_file, galaxy_shed_tool_conf_file, galaxy_shed_tool_path ):
    # We must make sure that functional.test_toolbox is always imported after database_contexts.galaxy_content
    # is set (which occurs in the main method before this method is called).  If functional.test_toolbox is
    # imported before database_contexts.galaxy_content is set, sa_session will be None in all methods that use it.
    import functional.test_toolbox as imported_test_toolbox
    global test_toolbox
    test_toolbox = imported_test_toolbox
    # Initialize a dictionary for the summary that will be printed to stdout.
    install_and_test_statistics_dict = install_and_test_base_util.initialize_install_and_test_statistics_dict()
    error_message = ''
    repositories_to_install, error_message = \
        install_and_test_base_util.get_repositories_to_install( install_and_test_base_util.galaxy_tool_shed_url, test_framework )
    if error_message:
        return None, error_message
    # Handle repositories not to be tested.
    print 'The exclude list file is defined as %s' % exclude_list_file
    if os.path.exists( exclude_list_file ):
        print 'Loading the list of repositories excluded from testing from the file %s...' % exclude_list_file
        # The following exclude_list will look something like this:
        # [{ 'reason': The default reason or the reason specified in this section,
        #    'repositories': [( name, owner, changeset_revision if changeset_revision else None ),
        #                     ( name, owner, changeset_revision if changeset_revision else None )]}]
        exclude_list_dicts = install_and_test_base_util.parse_exclude_list( exclude_list_file )
    else:
        print 'The exclude list file %s does not exist, so no repositories will be excluded from testing.' % exclude_list_file
        exclude_list_dicts = []
    # Generate a test method that will use Twill to install each repository into the embedded Galaxy application that was
    # started up, installing repository and tool dependencies. Upon successful installation, generate a test case for each
    # functional test defined for each tool in the repository and execute the test cases. Record the result of the tests.
    # The traceback and captured output of the tool that was run will be recored for test failures.  After all tests have
    # completed, the repository is uninstalled, so test cases don't interfere with the next repository's functional tests.
    for repository_dict in repositories_to_install:
        # Re-initialize the received galaxy_shed_tool_conf_file to be an empty shed_tool_conf.xml.
        install_and_test_base_util.populate_shed_conf_file( galaxy_shed_tool_conf_file, galaxy_shed_tool_path, xml_elems=None )
        encoded_repository_metadata_id = repository_dict.get( 'id', None )
        # Add the URL for the tool shed we're installing from, so the automated installation methods go to the right place.
        repository_dict[ 'tool_shed_url' ] = install_and_test_base_util.galaxy_tool_shed_url
        # Get the name and owner out of the repository info dict.
        name = str( repository_dict.get( 'name', '' ) )
        owner = str( repository_dict.get( 'owner', '' ) )
        changeset_revision = str( repository_dict.get( 'changeset_revision', '' ) )
        print "Processing revision %s of repository %s owned by %s..." % ( changeset_revision, name, owner )
        repository_identifier_tup = ( name, owner, changeset_revision )
        install_and_test_statistics_dict[ 'total_repositories_processed' ] += 1
        # Retrieve the stored list of tool_test_results_dicts.
        tool_test_results_dicts, error_message = \
            install_and_test_base_util.get_tool_test_results_dicts( install_and_test_base_util.galaxy_tool_shed_url,
                                                                    encoded_repository_metadata_id )
        if error_message:
            print 'Cannot install version %s of repository %s owned by %s due to the following error getting tool_test_results:\n%s' % \
                ( changeset_revision, name, owner, str( error_message ) )
        else:
            tool_test_results_dict = install_and_test_base_util.get_tool_test_results_dict( tool_test_results_dicts )
            is_excluded, reason = install_and_test_base_util.is_excluded( exclude_list_dicts,
                                                                          name,
                                                                          owner,
                                                                          changeset_revision,
                                                                          encoded_repository_metadata_id )
            if is_excluded:
                print "Not testing revision %s of repository %s owned by %s because it is in the exclude list for this test run." % \
                    ( changeset_revision, name, owner )
                # If this repository is being skipped, register the reason.
                tool_test_results_dict[ 'not_tested' ] = dict( reason=reason )
                params = dict( do_not_test=False )
                install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                                     tool_test_results_dicts,
                                                                                     tool_test_results_dict,
                                                                                     repository_dict,
                                                                                     params,
                                                                                     can_update_tool_shed )
            else:
                # See if the repository was installed in a previous test.
                repository = install_and_test_base_util.get_repository( name, owner, changeset_revision )
                if repository is None:
                    # The repository was not previously installed, so install it now.
                    start_time = time.time()
                    tool_test_results_dict = install_and_test_base_util.initialize_tool_tests_results_dict( app, tool_test_results_dict )
                    repository, error_message = install_and_test_base_util.install_repository( app, repository_dict )
                    if error_message:
                        remove_tests( app, repository )
                        # The repository installation failed.
                        print  'Installation failed for revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                        processed_repositories_with_installation_error = \
                            install_and_test_statistics_dict.get( 'repositories_with_installation_error', [] )
                        if repository_identifier_tup not in processed_repositories_with_installation_error:
                            install_and_test_statistics_dict[ 'repositories_with_installation_error' ].append( repository_identifier_tup )
                        current_repository_installation_error_dict = dict( tool_shed=install_and_test_base_util.galaxy_tool_shed_url,
                                                                           name=name,
                                                                           owner=owner,
                                                                           changeset_revision=changeset_revision,
                                                                           error_message=error_message )
                        tool_test_results_dict[ 'installation_errors' ][ 'current_repository' ].append( current_repository_installation_error_dict )
                        params = dict( test_install_error=True,
                                       do_not_test=False )
                        install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                                             tool_test_results_dicts,
                                                                                             tool_test_results_dict,
                                                                                             repository_dict,
                                                                                             params,
                                                                                             can_update_tool_shed )
                    else:
                        # The repository was successfully installed.
                        print 'Installation succeeded for revision %s of repository %s owned by %s.' % \
                            ( changeset_revision, name, owner )
                        # Add an empty 'missing_test_results' entry if it is missing from the tool_test_results_dict.  The 
                        # ~/tool_shed/scripts/check_repositories_for_functional_tests.py will have entered information in the
                        # 'missing_test_components' entry of the tool_test_results_dict dictionary for repositories that are
                        # missing test components.
                        if 'missing_test_components' not in tool_test_results_dict:
                            tool_test_results_dict[ 'missing_test_components' ] = []
                        # Hopefully we'll be able to run functional tests defined for tools contained in the repository - we'll
                        # assume so as the default.
                        can_run_functional_tests = True
                        # Populate the installation containers (success and error) for the repository's immediate dependencies
                        # (the entire dependency tree is not handled here).
                        params, install_and_test_statistics_dict, tool_test_results_dict = \
                            install_and_test_base_util.populate_dependency_install_containers( app,
                                                                                               repository,
                                                                                               repository_identifier_tup,
                                                                                               install_and_test_statistics_dict,
                                                                                               tool_test_results_dict )
                        if params.get( 'test_install_error', False ):
                            # We cannot run functional tests for contained tools due to dependency installation errors.
                            remove_tests( app, repository )
                            can_run_functional_tests = False
                            print 'Cannot execute tests for tools in revision %s of repository %s owned by %s ' % \
                                ( changeset_revision, name, owner )
                            print 'because one or more dependencies has installation errors.'
                            # The repository was successfully installed, but one or more dependencies had installation errors,
                            # so we'll populate the test result containers since we cannot execute any tests.
                            install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                                                 tool_test_results_dicts,
                                                                                                 tool_test_results_dict,
                                                                                                 repository_dict,
                                                                                                 params,
                                                                                                 can_update_tool_shed )
                        # Populate the installation containers (success or error) for the repository's immediate repository
                        # dependencies whose containers are not yet populated.
                        install_and_test_base_util.populate_install_containers_for_repository_dependencies( app,
                                                                                                            repository,
                                                                                                            encoded_repository_metadata_id,
                                                                                                            install_and_test_statistics_dict,
                                                                                                            can_update_tool_shed )
                        if can_run_functional_tests:
                            # Execute the contained tool's functional tests only if the repository's entire dependency
                            # tree is successfully installed.  The following checks should discover missing dependencies
                            # at any level of the dependency hierarchy.
                            missing_repository_dependencies = \
                                install_and_test_base_util.get_missing_repository_dependencies( repository,
                                                                                                all_missing_repository_dependencies=None )
                            print 'Missing repository dependencies:\n%s' % str( missing_repository_dependencies )
                            missing_tool_dependencies = \
                                install_and_test_base_util.get_missing_tool_dependencies( repository,
                                                                                          all_missing_tool_dependencies=None )
                            print 'Missing tool dependencies:\n%s' % str( missing_tool_dependencies )
                            if missing_repository_dependencies or missing_tool_dependencies:
                                # The repository was installed successfully, but one or more dependencies had installation errors.  Since
                                # we cannot test the tools due to these errors, we'll remove tests and tools were created during the repository
                                # installation process so nose will not discover them and attempt to execute them.
                                remove_tests( app, repository )
                                print 'Cannot execute tests for tools in revision %s of repository %s owned by %s ' % \
                                    ( changeset_revision, name, owner )
                                print 'because one or more dependencies has installation errors.'
                            else:
                                print 'Revision %s of repository %s owned by %s installed successfully, so running tool tests.' % \
                                    ( changeset_revision, name, owner )
                                # Generate the shed_tools_dict that specifies the location of test data contained within this repository.
                                # and configure and run functional tests for this repository. This is equivalent to
                                # sh run_functional_tests.sh -installed
                                install_and_test_base_util.populate_galaxy_shed_tools_dict_file( galaxy_shed_tools_dict_file,
                                                                                                 shed_tools_dict=None )
                                # Find the path to the test-data directory within the installed repository.
                                has_test_data, shed_tools_dict = \
                                    parse_tool_panel_config( galaxy_shed_tool_conf_file,
                                                             loads( file( galaxy_shed_tools_dict_file, 'r' ).read() ) )
                                # If the repository has a test-data directory we write the generated shed_tools_dict to a temporary
                                # file so the functional test framework can find it.
                                install_and_test_base_util.populate_galaxy_shed_tools_dict_file( galaxy_shed_tools_dict_file,
                                                                                                 shed_tools_dict=shed_tools_dict )
                                try:
                                    install_and_test_statistics_dict = test_repository_tools( app,
                                                                                              repository,
                                                                                              repository_dict,
                                                                                              tool_test_results_dicts,
                                                                                              tool_test_results_dict,
                                                                                              install_and_test_statistics_dict )
                                except Exception, e:
                                    remove_tests( app, repository )
                                    exception_message = 'Error executing tests for repository %s: %s' % ( name, str( e ) )
                                    log.exception( exception_message )
                                    tool_test_results_dict[ 'failed_tests' ].append( exception_message )
                                    processed_at_least_one_test_failed = \
                                        install_and_test_statistics_dict.get( 'at_least_one_test_failed', [] )
                                    if repository_identifier_tup not in processed_at_least_one_test_failed:
                                        install_and_test_statistics_dict[ 'at_least_one_test_failed' ].append( repository_identifier_tup )
                                    # Record the status of this repository in the tool shed.
                                    params[ 'tools_functionally_correct' ] = False
                                    install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                                                         tool_test_results_dicts,
                                                                                                         tool_test_results_dict,
                                                                                                         repository_dict,
                                                                                                         params,
                                                                                                         can_update_tool_shed )
                    print '\nAttempting to install revision %s of repository %s owned by %s took %s seconds.\n' % \
                        ( changeset_revision, name, owner, str( time.time() - start_time ) )
                else:
                    remove_tests( app, repository )
                    print 'Skipped attempt to install revision %s of repository %s owned by %s because ' % \
                        ( changeset_revision, name, owner )
                    print 'it was previously installed and currently has status %s' % str( repository.status )
    return install_and_test_statistics_dict, error_message

def main():
    if install_and_test_base_util.tool_shed_api_key is None:
        # If the tool shed URL specified in any dict is not present in the tool_sheds_conf.xml, the installation will fail.
        log.debug( 'Cannot proceed without a valid tool shed API key set in the enviroment variable GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY.' )
        return 1
    if install_and_test_base_util.galaxy_tool_shed_url is None:
        log.debug( 'Cannot proceed without a valid Tool Shed base URL set in the environment variable GALAXY_INSTALL_TEST_TOOL_SHED_URL.' )
        return 1
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST', install_and_test_base_util.default_galaxy_test_host )
    # Set the GALAXY_INSTALL_TEST_HOST variable so that Twill will have the Galaxy url to which to
    # install repositories.
    os.environ[ 'GALAXY_INSTALL_TEST_HOST' ] = galaxy_test_host
    # Set the GALAXY_TEST_HOST environment variable so that the toolbox tests will have the Galaxy url
    # on which to to run tool functional tests.
    os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
    galaxy_test_port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT', str( install_and_test_base_util.default_galaxy_test_port_max ) )
    os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_port
    tool_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_PATH', 'tools' )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_INSTALL_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.abspath( galaxy_test_file_dir )
    use_distributed_object_store = os.environ.get( 'GALAXY_INSTALL_TEST_USE_DISTRIBUTED_OBJECT_STORE', False )
    if not os.path.isdir( galaxy_test_tmp_dir ):
        os.mkdir( galaxy_test_tmp_dir )
    # Set up the configuration files for the Galaxy instance.
    galaxy_shed_tool_path = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_PATH',
                                            tempfile.mkdtemp( dir=galaxy_test_tmp_dir, prefix='shed_tools' ) )
    shed_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF',
                                                     os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_data_table_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF',
                                                       install_and_test_base_util.tool_data_table_conf )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_CONF',
                                            os.path.join( galaxy_test_tmp_dir, 'test_tool_conf.xml' ) )
    galaxy_job_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_JOB_CONF',
                                           os.path.join( galaxy_test_tmp_dir, 'test_job_conf.xml' ) )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF',
                                                 os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_MIGRATED_TOOL_CONF',
                                                     os.path.join( galaxy_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF',
                                                  os.path.join( galaxy_test_tmp_dir, 'test_tool_sheds_conf.xml' ) )
    galaxy_shed_tools_dict_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DICT_FILE',
                                                       os.path.join( galaxy_test_tmp_dir, 'shed_tool_dict' ) )
    install_and_test_base_util.populate_galaxy_shed_tools_dict_file( galaxy_shed_tools_dict_file, shed_tools_dict=None )
    # Set the GALAXY_TOOL_SHED_TEST_FILE environment variable to the path of the shed_tools_dict file so that
    # test.base.twilltestcase.setUp will find and parse it properly.
    os.environ[ 'GALAXY_TOOL_SHED_TEST_FILE' ] = galaxy_shed_tools_dict_file
    if 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' ] = tool_data_path
    # Configure the database connection and path.
    if 'GALAXY_INSTALL_TEST_DBPATH' in os.environ:
        galaxy_db_path = os.environ[ 'GALAXY_INSTALL_TEST_DBPATH' ]
    else:
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        galaxy_db_path = os.path.join( tempdir, 'database' )
    # Configure the paths Galaxy needs to install and test tools.
    galaxy_file_path = os.path.join( galaxy_db_path, 'files' )
    new_repos_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_tempfiles = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_migrated_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    # Set up the tool dependency path for the Galaxy instance.
    tool_dependency_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR', None )
    if tool_dependency_dir is None:
        tool_dependency_dir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR' ] = tool_dependency_dir
    os.environ[ 'GALAXY_TOOL_DEPENDENCY_DIR' ] = tool_dependency_dir
    if 'GALAXY_INSTALL_TEST_DBURI' in os.environ:
        database_connection = os.environ[ 'GALAXY_INSTALL_TEST_DBURI' ]
    else:
        database_connection = 'sqlite:///' + os.path.join( galaxy_db_path, 'install_and_test_repositories.sqlite' )
    if 'GALAXY_INSTALL_TEST_INSTALL_DBURI' in os.environ:
        install_database_connection = os.environ[ 'GALAXY_INSTALL_TEST_INSTALL_DBURI' ]
    elif asbool( os.environ.get( 'GALAXY_TEST_INSTALL_DB_MERGED', default_install_db_merged ) ):
        install_database_connection = database_connection
    else:
        install_galaxy_db_path = os.path.join( galaxy_db_path, 'install.sqlite' )
        install_database_connection = 'sqlite:///%s' % install_galaxy_db_path
    kwargs = {}
    for dir in [ galaxy_test_tmp_dir ]:
        try:
            os.makedirs( dir )
        except OSError:
            pass
    print "Database connection: ", database_connection
    print "Install database connection: ", install_database_connection
    # Generate the shed_tool_data_table_conf.xml file.
    file( shed_tool_data_table_conf_file, 'w' ).write( install_and_test_base_util.tool_data_table_conf_xml_template )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF' ] = shed_tool_data_table_conf_file
    # ---- Start up a Galaxy instance ------------------------------------------------------
    # Generate the tool_conf.xml file.
    file( galaxy_tool_conf_file, 'w' ).write( install_and_test_base_util.tool_conf_xml )
    # Generate the job_conf.xml file.
    file( galaxy_job_conf_file, 'w' ).write( install_and_test_base_util.job_conf_xml )
    # Generate the tool_sheds_conf.xml file, but only if a the user has not specified an existing one in the environment.
    if 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF' not in os.environ:
        file( galaxy_tool_sheds_conf_file, 'w' ).write( install_and_test_base_util.tool_sheds_conf_xml )
    # Generate the shed_tool_conf.xml file.
    install_and_test_base_util.populate_shed_conf_file( galaxy_shed_tool_conf_file, galaxy_shed_tool_path, xml_elems=None )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF' ] = galaxy_shed_tool_conf_file
    # Generate the migrated_tool_conf.xml file.
    install_and_test_base_util.populate_shed_conf_file( galaxy_migrated_tool_conf_file, galaxy_migrated_tool_path, xml_elems=None )
    # Write the embedded web application's specific configuration to a temporary file. This is necessary in order for
    # the external metadata script to find the right datasets.
    kwargs = dict( admin_users = 'test@bx.psu.edu',
                   master_api_key = install_and_test_base_util.default_galaxy_master_api_key,
                   allow_user_creation = True,
                   allow_user_deletion = True,
                   allow_library_path_paste = True,
                   database_connection = database_connection,
                   datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                   file_path = galaxy_file_path,
                   id_secret = install_and_test_base_util.galaxy_encode_secret,
                   install_database_connection = install_database_connection,
                   job_config_file = galaxy_job_conf_file,
                   job_queue_workers = 5,
                   log_destination = "stdout",
                   migrated_tools_config = galaxy_migrated_tool_conf_file,
                   new_file_path = galaxy_tempfiles,
                   running_functional_tests = True,
                   shed_tool_data_table_config = shed_tool_data_table_conf_file,
                   shed_tool_path = galaxy_shed_tool_path,
                   template_path = "templates",
                   tool_config_file = ','.join( [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ] ),
                   tool_data_path = tool_data_path,
                   tool_data_table_config_path = galaxy_tool_data_table_conf_file,
                   tool_dependency_dir = tool_dependency_dir,
                   tool_path = tool_path,
                   tool_parse_help = False,
                   tool_sheds_config_file = galaxy_tool_sheds_conf_file,
                   update_integrated_tool_panel = False,
                   use_heartbeat = False )
    galaxy_config_file = os.environ.get( 'GALAXY_INSTALL_TEST_INI_FILE', None )
    # If the user has passed in a path for the .ini file, do not overwrite it.
    if not galaxy_config_file:
        galaxy_config_file = os.path.join( galaxy_test_tmp_dir, 'install_test_tool_shed_repositories_wsgi.ini' )
        config_items = []
        for label in kwargs:
            config_tuple = label, kwargs[ label ]
            config_items.append( config_tuple )
        # Write a temporary file, based on galaxy.ini.sample, using the configuration options defined above.
        generate_config_file( 'config/galaxy.ini.sample', galaxy_config_file, config_items )
    # kwargs must be a list when passed to the Galaxy webapp (i.e., UniverseApplication).
    # The following is used to set metadata externally.
    kwargs[ 'tool_config_file' ] = [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ]
    # Set the global_conf[ '__file__' ] option to the location of the temporary .ini file, which gets passed to set_metadata.sh.
    kwargs[ 'global_conf' ] = install_and_test_base_util.get_webapp_global_conf()
    kwargs[ 'global_conf' ][ '__file__' ] = galaxy_config_file
    # ---- Build Galaxy Application --------------------------------------------------
    if not database_connection.startswith( 'sqlite://' ):
        kwargs[ 'database_engine_option_max_overflow' ] = '20'
        kwargs[ 'database_engine_option_pool_size' ] = '10'
    kwargs[ 'config_file' ] = galaxy_config_file
    app = UniverseApplication( **kwargs )
    database_contexts.galaxy_context = app.model.context
    database_contexts.install_context = app.install_model.context
    log.debug( "Embedded Galaxy application started..." )
    # ---- Run galaxy webserver ------------------------------------------------------
    server = None
    global_conf = install_and_test_base_util.get_webapp_global_conf()
    global_conf[ 'database_file' ] = database_connection
    webapp = buildapp.app_factory( global_conf,
                                   use_translogger=False,
                                   static_enabled=install_and_test_base_util.STATIC_ENABLED,
                                   app=app )
    # Serve the app on a specified or random port.
    if galaxy_test_port is not None:
        server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                galaxy_test_port = str( random.randint( install_and_test_base_util.default_galaxy_test_port_min,
                                                        install_and_test_base_util.default_galaxy_test_port_max ) )
                log.debug( "Attempting to serve app on randomly chosen port: %s", galaxy_test_port )
                server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
                break
            except socket.error, e:
                if e[0] == 98:
                    continue
                raise
        else:
            raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % \
                ( install_and_test_base_util.default_galaxy_test_port_min, install_and_test_base_util.default_galaxy_test_port_max ) )
    os.environ[ 'GALAXY_INSTALL_TEST_PORT' ] = galaxy_test_port
    # Start the server.
    t = threading.Thread( target=server.serve_forever )
    t.start()
    # Test if the server is up.
    for i in range( 10 ):
        # Directly test the app, not the proxy.
        conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port )
        conn.request( "GET", "/" )
        if conn.getresponse().status == 200:
            break
        time.sleep( 0.1 )
    else:
        raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
    log.debug( "Embedded galaxy web server started..." )
    log.debug( "The embedded Galaxy application is running on %s:%s" % ( str( galaxy_test_host ), str( galaxy_test_port ) ) )
    log.debug( "Repositories will be installed from the tool shed at %s" % str( install_and_test_base_util.galaxy_tool_shed_url ) )
    # If a tool_data_table_conf.test.xml file was found, add the entries from it into the app's tool data tables.
    if install_and_test_base_util.additional_tool_data_tables:
        app.tool_data_tables.add_new_entries_from_config_file( config_filename=install_and_test_base_util.additional_tool_data_tables,
                                                               tool_data_path=install_and_test_base_util.additional_tool_data_path,
                                                               shed_tool_data_table_config=None,
                                                               persist=False )
    now = time.strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - installation script for repositories containing tools started." % now
    if not can_update_tool_shed:
        print "# This run will not update the Tool Shed database."
    print "####################################################################################"
    install_and_test_statistics_dict, error_message = install_and_test_repositories( app,
                                                                                     galaxy_shed_tools_dict_file,
                                                                                     galaxy_shed_tool_conf_file,
                                                                                     galaxy_shed_tool_path )
    try:
        install_and_test_base_util.print_install_and_test_results( 'repositories with tools',
                                                                   install_and_test_statistics_dict,
                                                                   error_message )
    except Exception, e:
        log.exception( 'Attempting to print the following dictionary...\n\n%s\n\n...threw the following exception...\n\n%s\n\n' % \
            ( str( install_and_test_statistics_dict ), str( e ) ) )
    log.debug( "Shutting down..." )
    # Gracefully shut down the embedded web server and UniverseApplication.
    if server:
        log.debug( "Shutting down embedded galaxy web server..." )
        server.server_close()
        server = None
        log.debug( "Embedded galaxy server stopped..." )
    if app:
        log.debug( "Shutting down galaxy application..." )
        app.shutdown()
        app = None
        log.debug( "Embedded galaxy application stopped..." )
    # Clean up test files unless otherwise specified.
    if 'GALAXY_INSTALL_TEST_NO_CLEANUP' not in os.environ:
        for dir in [ galaxy_test_tmp_dir ]:
            if os.path.exists( dir ):
                try:
                    shutil.rmtree( dir )
                    log.debug( "Cleaned up temporary files in %s", str( dir ) )
                except:
                    pass
    else:
        log.debug( 'GALAXY_INSTALL_TEST_NO_CLEANUP set, not cleaning up.' )
    # Return a "successful" response to buildbot.
    return 0

def remove_tests( app, repository ):
    """
    Delete any configured tool functional tests from the test_toolbox.__dict__.
    """
    print '\n-------------------------------------------------------------\n'
    if repository:
        print 'Removing tests and tool ids for revision %s of repository %s owned by %s' % \
            ( str( repository.changeset_revision ), str( repository.name ), str( repository.owner ) )
    else:
        print 'Removing tests and tool ids when received repository is None...'
    print 'app.toolbox.tools_by_id.keys():\n%s\n' % str( app.toolbox.tools_by_id.keys() )
    tests_to_delete = []
    tools_to_delete_by_id = []
    for key in test_toolbox.__dict__:
        if key.startswith( 'TestForTool_' ):
            # We can't delete this test just yet, we're still iterating over __dict__.
            tests_to_delete.append( key )
            tool_id = key.replace( 'TestForTool_', '' )
            for app_tool_id in app.toolbox.tools_by_id:
                # Revisit this code if at some point we notice that Twill re-runs tests that should have been deleted.
                # Undoubtedly the following if statement will need to be enhanced to find the tool id in question. For
                # example, the following or is required because Twill replaces some spaces with underscores in test names.
                if app_tool_id == tool_id:
                    print 'Setting tool id %s for deletion from app.toolbox[ tools_by_id ].' % str( app_tool_id )
                    tools_to_delete_by_id.append( app_tool_id )
                else:
                    reset_spaces_app_tool_id = app_tool_id.replace( '_', ' ' )
                    reset_spaces_tool_id = tool_id.replace( '_', ' ' )
                    if reset_spaces_app_tool_id == reset_spaces_tool_id:
                        print 'Setting tool id %s for deletion from app.toolbox[ tools_by_id ].' % str( app_tool_id )
                        tools_to_delete_by_id.append( app_tool_id )
    if repository:
        metadata = repository.metadata
        print 'metadata:\n%s\n' % str( metadata )
        if metadata:
            tools = metadata.get( 'tools', [] )
            print 'tools:\n%s\n' % str( tools )
            for tool_dict in tools:
                print 'tool_dict:\n%s\n' % str( tool_dict )
                guid = tool_dict.get( 'guid', None )
                print 'guid:\n%s\n' % str( guid )
                if guid:
                    if guid in app.toolbox.tools_by_id:
                        print 'Setting tool id %s for deletion from app.toolbox[ tools_by_id ].' % str( guid )
                        tools_to_delete_by_id.append( guid )
    # Delete the discovered twill-generated tests.
    for key in tests_to_delete:
        if key in test_toolbox.__dict__:
            print 'Deleting test %s from test_toolbox.' % str( key )
            del test_toolbox.__dict__[ key ]
    for tool_id in tools_to_delete_by_id:
        if tool_id in app.toolbox.tools_by_id:
            print 'Deleting tool id %s from app.toolbox[ tools_by_id ].' % str( tool_id )
            del app.toolbox.tools_by_id[ tool_id ]
    print '\n-------------------------------------------------------------\n'

def test_repository_tools( app, repository, repository_dict, tool_test_results_dicts, tool_test_results_dict,
                           install_and_test_statistics_dict ):
    """Test tools contained in the received repository."""
    # Get the attributes that identify the repository whose contained tools are being tested.
    name = str( repository.name )
    owner = str( repository.owner )
    changeset_revision = str( repository.changeset_revision )
    repository_identifier_tup = ( name, owner, changeset_revision )
    print 'Testing tools contained in revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
    # Generate the test methods for this installed repository. We need to pass testing_shed_tools=True here
    # or twill will look in $GALAXY_HOME/test-data for test data, which may result in missing or invalid test
    # files.
    test_toolbox.build_tests( app=app,
                              testing_shed_tools=True,
                              master_api_key=install_and_test_base_util.default_galaxy_master_api_key )
    # Set up nose to run the generated functional tests.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the configured tests.
    result, test_plugins = install_and_test_base_util.run_tests( test_config )
    if result.wasSuccessful():
        # This repository's tools passed all functional tests.  Use the ReportResults nose plugin to get a list
        # of tests that passed.
        print 'Revision %s of repository %s owned by %s installed and passed functional tests.' % \
            ( changeset_revision, name, owner )
        for plugin in test_plugins:
            if hasattr( plugin, 'getTestStatus' ):
                test_identifier = '%s/%s' % ( owner, name )
                passed_tests = plugin.getTestStatus( test_identifier )
                break
        tool_test_results_dict[ 'passed_tests' ] = []
        for test_id in passed_tests:
            # Normalize the tool ID and version display.
            tool_id, tool_version = get_tool_info_from_test_id( test_id )
            test_result = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
            tool_test_results_dict[ 'passed_tests' ].append( test_result )
        # Update the repository_metadata table in the tool shed's database to include the passed tests.
        processed_all_tests_passed = install_and_test_statistics_dict.get( 'all_tests_passed', [] )
        if repository_identifier_tup not in processed_all_tests_passed:
            install_and_test_statistics_dict[ 'all_tests_passed' ].append( repository_identifier_tup )
        params = dict( tools_functionally_correct=True,
                       do_not_test=False,
                       test_install_error=False )
        # Call the save_test_results_for_changeset_revision() method to execute a PUT request to the
        # repository_revisions API controller with the status of the test. This also sets the do_not_test
        # and tools_functionally correct flags and updates the time_last_tested field to today's date.
        install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                             tool_test_results_dicts,
                                                                             tool_test_results_dict,
                                                                             repository_dict,
                                                                             params,
                                                                             can_update_tool_shed )
    else:
        # The get_failed_test_dicts() method returns a list.
        print 'Revision %s of repository %s owned by %s installed successfully but did not pass functional tests.' % \
            ( changeset_revision, name, owner )
        failed_test_dicts = get_failed_test_dicts( result, from_tool_test=True )
        tool_test_results_dict[ 'failed_tests' ] = failed_test_dicts
        processed_at_least_one_test_failed = install_and_test_statistics_dict.get( 'at_least_one_test_failed', [] )
        if repository_identifier_tup not in processed_at_least_one_test_failed:
            install_and_test_statistics_dict[ 'at_least_one_test_failed' ].append( repository_identifier_tup )
        is_latest_downloadable_revision, error_message = \
            install_and_test_base_util.is_latest_downloadable_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                        repository_dict )
        if is_latest_downloadable_revision is None or error_message:
            print 'Error attempting to determine if revision %s of repository %s owned by %s ' % \
                ( changeset_revision, name, owner )
            print 'is the latest downloadable revision: %s' % error_message
            set_do_not_test = False
        else:
            set_do_not_test = not is_latest_downloadable_revision
        params = dict( tools_functionally_correct=False,
                       test_install_error=False,
                       do_not_test=set_do_not_test )
        install_and_test_base_util.save_test_results_for_changeset_revision( install_and_test_base_util.galaxy_tool_shed_url,
                                                                             tool_test_results_dicts,
                                                                             tool_test_results_dict,
                                                                             repository_dict,
                                                                             params,
                                                                             can_update_tool_shed )
    # Remove the just-executed tests so twill will not find and re-test them along with the tools
    # contained in the next repository.
    remove_tests( app, repository )
    return install_and_test_statistics_dict

if __name__ == "__main__":
    # The tool_test_results_dict should always have the following structure:
    # {
    #     "test_environment":
    #         {
    #              "galaxy_revision": "9001:abcd1234",
    #              "galaxy_database_version": "114",
    #              "tool_shed_revision": "9001:abcd1234",
    #              "tool_shed_mercurial_version": "2.3.1",
    #              "tool_shed_database_version": "17",
    #              "python_version": "2.7.2",
    #              "architecture": "x86_64",
    #              "system": "Darwin 12.2.0"
    #         },
    #      "passed_tests":
    #         [
    #             {
    #                 "test_id": "The test ID, generated by twill",
    #                 "tool_id": "The tool ID that was tested",
    #                 "tool_version": "The tool version that was tested",
    #             },
    #         ]
    #     "failed_tests":
    #         [
    #             {
    #                 "test_id": "The test ID, generated by twill",
    #                 "tool_id": "The tool ID that was tested",
    #                 "tool_version": "The tool version that was tested",
    #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
    #                 "traceback": "The captured traceback."
    #             },
    #         ]
    #     "installation_errors":
    #         {
    #              'tool_dependencies':
    #                  [
    #                      {
    #                         'type': 'Type of tool dependency, e.g. package, set_environment, etc.',
    #                         'name': 'Name of the tool dependency.',
    #                         'version': 'Version if this is a package, otherwise blank.',
    #                         'error_message': 'The error message returned when installation was attempted.',
    #                      },
    #                  ],
    #              'repository_dependencies':
    #                  [
    #                      {
    #                         'tool_shed': 'The tool shed that this repository was installed from.',
    #                         'name': 'The name of the repository that failed to install.',
    #                         'owner': 'Owner of the failed repository.',
    #                         'changeset_revision': 'Changeset revision of the failed repository.',
    #                         'error_message': 'The error message that was returned when the repository failed to install.',
    #                      },
    #                  ],
    #              'current_repository':
    #                  [
    #                      {
    #                         'tool_shed': 'The tool shed that this repository was installed from.',
    #                         'name': 'The name of the repository that failed to install.',
    #                         'owner': 'Owner of the failed repository.',
    #                         'changeset_revision': 'Changeset revision of the failed repository.',
    #                         'error_message': 'The error message that was returned when the repository failed to install.',
    #                      },
    #                  ],
    #             {
    #                 "name": "The name of the repository.",
    #                 "owner": "The owner of the repository.",
    #                 "changeset_revision": "The changeset revision of the repository.",
    #                 "error_message": "The message stored in tool_dependency.error_message."
    #             },
    #         }
    #      "missing_test_components":
    #         [
    #             {
    #                 "tool_id": "The tool ID that missing components.",
    #                 "tool_version": "The version of the tool."
    #                 "tool_guid": "The guid of the tool."
    #                 "missing_components": "Which components are missing, e.g. the test data filename, or the test-data directory."
    #             },
    #         ]
    #      "not_tested":
    #         {
    #             "reason": "The Galaxy development team has determined that this repository should not be installed and tested by the automated framework."
    #         }
    # }
    sys.exit( main() )
