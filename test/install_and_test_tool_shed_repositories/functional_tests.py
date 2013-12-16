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

test_toolbox = None
import httplib
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
import install_and_test_tool_shed_repositories.functional.test_install_repositories as test_install_repositories
import logging
import nose
import platform
import random
import re
import shutil
import socket
import string
import tempfile
import time
import threading
import tool_shed.util.shed_util_common as suc
import urllib

from base.tool_shed_util import log_reason_repository_cannot_be_uninstalled
from base.tool_shed_util import parse_tool_panel_config
from install_and_test_tool_shed_repositories.base.util import get_database_version
from install_and_test_tool_shed_repositories.base.util import get_repository_current_revision
from common import update
from datetime import datetime
from galaxy.app import UniverseApplication
from galaxy.util import asbool
from galaxy.util import listify
from galaxy.util import unicodify
from galaxy.util.json import from_json_string
from galaxy.util.json import to_json_string
from galaxy.web import buildapp
from galaxy.web.framework.helpers import time_ago
from functional_tests import generate_config_file
from mercurial import __version__
from nose.plugins import Plugin
from paste import httpserver
from tool_shed.util import tool_dependency_util
from tool_shed.util.xml_util import parse_xml

from functional import database_contexts

log = logging.getLogger( 'install_and_test_repositories' )

assert sys.version_info[ :2 ] >= ( 2, 6 )
test_home_directory = os.path.join( cwd, 'test', 'install_and_test_tool_shed_repositories' )
default_test_file_dir = os.path.join( test_home_directory, 'test_data' )

# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the database, new repositories, etc.
galaxy_test_tmp_dir = os.path.join( test_home_directory, 'tmp' )
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"
os.environ[ 'GALAXY_INSTALL_TEST_TMP_DIR' ] = galaxy_test_tmp_dir

default_galaxy_test_port_min = 10000
default_galaxy_test_port_max = 10999
default_galaxy_test_host = '127.0.0.1'
# The following should be an actual value (not None).  If developers manually specify their
# tests to use the API it will not work unless a master API key is specified.
default_galaxy_master_api_key = 123456

# This script can be run in such a way that no Tool Shed database records should be changed.
if '-info_only' in sys.argv or 'GALAXY_INSTALL_TEST_INFO_ONLY' in os.environ:
    can_update_tool_shed = False
else:
    can_update_tool_shed = True

# Should this serve static resources (scripts, images, styles, etc.)?
STATIC_ENABLED = True

# Set up a job_conf.xml that explicitly limits jobs to 10 minutes.
job_conf_xml = '''<?xml version="1.0"?>
<!-- A test job config that explicitly configures job running the way it is configured by default (if there is no explicit config). -->
<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="4"/>
    </plugins>
    <handlers>
        <handler id="main"/>
    </handlers>
    <destinations>
        <destination id="local" runner="local"/>
    </destinations>
    <limits>
        <limit type="walltime">00:10:00</limit>
    </limits>
</job_conf>
'''

# Create a blank shed_tool_conf.xml to define the installed repositories.
shed_tool_conf_xml_template = '''<?xml version="1.0"?>
<toolbox tool_path="${shed_tool_path}">
</toolbox>
'''

# Since we will be running functional tests we'll need the upload tool, but the rest can be omitted.
tool_conf_xml = '''<?xml version="1.0"?>
<toolbox>
    <section name="Get Data" id="getext">
        <tool file="data_source/upload.xml"/>
    </section>
</toolbox>
'''

# Set up an empty shed_tool_data_table_conf.xml.
tool_data_table_conf_xml_template = '''<?xml version="1.0"?>
<tables>
</tables>
'''

# Optionally set the environment variable GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF to the location of a
# tool shed's configuration file that includes the tool shed from which repositories will be installed.
tool_sheds_conf_xml = '''<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="Galaxy main tool shed" url="http://toolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Galaxy test tool shed" url="http://testtoolshed.g2.bx.psu.edu/"/>
</tool_sheds>
'''

# If we have a tool_data_table_conf.test.xml, set it up to be loaded when the UniverseApplication is started.
# This allows one to specify a set of tool data that is used exclusively for testing, and not loaded into any
# Galaxy instance. By default, this will be in the test-data-repo/location directory generated by buildbot_setup.sh.
if os.path.exists( 'tool_data_table_conf.test.xml' ):
    additional_tool_data_tables = 'tool_data_table_conf.test.xml'
    additional_tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_EXTRA_TOOL_DATA_PATH',
                                                os.path.join( 'test-data-repo', 'location' ) )
else:
    additional_tool_data_tables = None
    additional_tool_data_path = None

# Set up default tool data tables.
if os.path.exists( 'tool_data_table_conf.xml' ):
    tool_data_table_conf = 'tool_data_table_conf.xml'
elif os.path.exists( 'tool_data_table_conf.xml.sample' ):
    tool_data_table_conf = 'tool_data_table_conf.xml.sample'
else:
    tool_data_table_conf = None

# The GALAXY_INSTALL_TEST_TOOL_SHED_URL and GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY environment variables must be
# set for this script to work correctly.  If the value of GALAXY_INSTALL_TEST_TOOL_SHED_URL does not refer to one
# of the defaults, the GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF must refer to a tool shed configuration file that contains
# a definition for that tool shed.
galaxy_tool_shed_url = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_URL', None )
tool_shed_api_key = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY', None )
exclude_list_file = os.environ.get( 'GALAXY_INSTALL_TEST_EXCLUDE_REPOSITORIES', 'install_test_exclude.xml' )
    
if 'GALAXY_INSTALL_TEST_SECRET' not in os.environ:
    galaxy_encode_secret = 'changethisinproductiontoo'
    os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ] = galaxy_encode_secret
else:
    galaxy_encode_secret = os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ]

testing_single_repository = {}
if 'repository_name' in os.environ and 'repository_owner' in os.environ:
    testing_single_repository[ 'name' ] = os.environ[ 'repository_name' ]
    testing_single_repository[ 'owner' ] = os.environ[ 'repository_owner' ]
    if 'repository_revision' in os.environ:
        testing_single_repository[ 'changeset_revision' ] = os.environ[ 'repository_revision' ]
    else:
        testing_single_repository[ 'changeset_revision' ] = None


class ReportResults( Plugin ):
    '''Simple Nose plugin to record the IDs of all tests run, regardless of success.'''
    name = "reportresults"
    passed = {}

    def options( self, parser, env=os.environ ):
        super( ReportResults, self ).options( parser, env=env )

    def configure(self, options, conf):
        super( ReportResults, self ).configure( options, conf )
        if not self.enabled:
            return

    def addSuccess( self, test ):
        '''Only record test IDs that correspond to tool functional tests.'''
        if 'TestForTool' in test.id():
            test_id = test.id()
            # Rearrange the test ID to match the format that is produced in test_results.failures
            test_id_parts = test_id.split( '.' )
            fixed_test_id = '%s (%s)' % ( test_id_parts[ -1 ], '.'.join( test_id_parts[ :-1 ] ) )
            test_parts = fixed_test_id.split( '/' )
            owner = test_parts[ -4 ]
            name = test_parts[ -3 ]
            test_identifier = '%s/%s' % ( owner, name )
            if test_identifier not in self.passed:
                self.passed[ test_identifier ] = []
            self.passed[ test_identifier ].append( fixed_test_id )

    def getTestStatus( self, test_identifier ):
        if test_identifier in self.passed:
            passed_tests = self.passed[ test_identifier ]
            del self.passed[ test_identifier ]
            return passed_tests
        return []

def deactivate_repository( app, repository_dict ):
    sa_session = app.install_model.context
    # Clean out any generated tests. This is necessary for Twill.
    remove_generated_tests( app )
    # The dict contains the only repository the app should have installed at this point.
    name = str( repository_dict[ 'name' ] )
    owner = str( repository_dict[ 'owner' ] )
    changeset_revision = str( repository_dict[ 'changeset_revision' ] )
    repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
    repository_dict_for_deactivation = dict( name=name,
                                             owner=owner,
                                             changeset_revision=changeset_revision )
    log.debug( 'Changeset revision %s of repository %s owned by %s selected for deactivation.' % ( changeset_revision, name, owner ) )
    test_install_repositories.generate_deactivate_method( repository_dict_for_deactivation )
    # Set up nose to run the generated uninstall method as a functional test.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the deactivate method which uses the Galaxy web interface to deactivate the repository.
    result, _ = run_tests( test_config )
    success = result.wasSuccessful()
    if not success:
        log.debug( 'Deactivation of revision %s repository %s owned by %s failed.' % ( changeset_revision, name, owner ) )

def get_api_url( base, parts=[], params=None ):
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts:
        parts.insert( 0, 'api' )
    url = suc.url_join( base, *parts )
    if params is not None:
        query_string = urllib.urlencode( params )
        url += '?%s' % query_string
    return url

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

def get_latest_downloadable_changeset_revision( url, name, owner ):
    error_message = ''
    parts = [ 'api', 'repositories', 'get_ordered_installable_revisions' ]
    params = dict( name=name, owner=owner )
    api_url = get_api_url( base=url, parts=parts, params=params )
    changeset_revisions, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    if changeset_revisions:
        return changeset_revisions[ -1 ], error_message
    else:
        return suc.INITIAL_CHANGELOG_HASH, error_message

def get_missing_tool_dependencies( repository ):
    log.debug( 'Checking %s repository %s for missing tool dependencies.' % ( repository.status, repository.name ) )
    missing_tool_dependencies = repository.missing_tool_dependencies
    for tool_dependency in repository.tool_dependencies:
        log.debug( 'Tool dependency %s version %s has status %s.' % ( tool_dependency.name, tool_dependency.version, tool_dependency.status ) )
    for repository_dependency in repository.repository_dependencies:
        if repository_dependency.includes_tool_dependencies:
            missing_tool_dependencies.extend( get_missing_tool_dependencies( repository_dependency ) )
    return missing_tool_dependencies

def get_repository_dict( url, repository_dict ):
    error_message = ''
    parts = [ 'api', 'repositories', repository_dict[ 'repository_id' ] ]
    api_url = get_api_url( base=url, parts=parts )
    extended_dict, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    name = str( extended_dict[ 'name' ] )
    owner = str( extended_dict[ 'owner' ] )
    latest_changeset_revision, error_message = get_latest_downloadable_changeset_revision( url, name, owner )
    if error_message:
        return None, error_message
    extended_dict[ 'latest_revision' ] = str( latest_changeset_revision )
    return extended_dict, error_message

def get_repository_tuple_from_elem( elem ):
    attributes = elem.attrib
    name = attributes.get( 'name', None )
    owner = attributes.get( 'owner', None )
    changeset_revision = attributes.get( 'changeset_revision', None )
    return ( name, owner, changeset_revision )

def get_repositories_to_install( tool_shed_url ):
    """
    Get a list of repository info dicts to install. This method expects a json list of dicts with the following structure:
    [{ "changeset_revision": <revision>,
       "encoded_repository_id": <encoded repository id from the tool shed>,
       "name": <name>,
       "owner": <owner>,
       "tool_shed_url": <url> }]
    """
    error_message = ''
    latest_revision_only = '-check_all_revisions' not in sys.argv
    if latest_revision_only:
        log.debug( 'Testing is restricted to the latest downloadable revision in this test run.' )
    repository_dicts = []
    parts = [ 'repository_revisions' ]
    params = dict( do_not_test='false',
                   downloadable='true',
                   includes_tools='true',
                   malicious='false',
                   missing_test_components='false',
                   skip_tool_test='false' )
    api_url = get_api_url( base=tool_shed_url, parts=parts, params=params )
    baseline_repository_dicts, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    for baseline_repository_dict in baseline_repository_dicts:
        # We need to get some details from the tool shed API, such as repository name and owner, to pass on to the
        # module that will generate the install methods.
        repository_dict, error_message = get_repository_dict( galaxy_tool_shed_url, baseline_repository_dict )
        if error_message:
            log.debug( 'Error getting additional details from the API: %s' % str(  error_message ) )
        else:
            # Don't test empty repositories.
            changeset_revision = baseline_repository_dict[ 'changeset_revision' ]
            if changeset_revision != suc.INITIAL_CHANGELOG_HASH:
                # Merge the dictionary returned from /api/repository_revisions with the detailed repository_dict and
                # append it to the list of repository_dicts to install and test.
                if latest_revision_only:
                    latest_revision = repository_dict[ 'latest_revision' ]
                    if changeset_revision == latest_revision:
                        repository_dicts.append( dict( repository_dict.items() + baseline_repository_dict.items() ) )
                else:
                    repository_dicts.append( dict( repository_dict.items() + baseline_repository_dict.items() ) )
    if testing_single_repository:
        tsr_name = testing_single_repository[ 'name' ]
        tsr_owner = testing_single_repository[ 'owner' ]
        tsr_changeset_revision = testing_single_repository[ 'changeset_revision' ]
        log.debug( 'Testing single repository with name %s and owner %s.' % ( str( tsr_name ), str( tsr_owner ) ) )
        for repository_to_install in repository_dicts:
            rti_name = repository_to_install[ 'name' ]
            rti_owner = repository_to_install[ 'owner' ]
            rti_changeset_revision = repository_to_install[ 'changeset_revision' ]
            if rti_name == tsr_name and rti_owner == tsr_owner:
                if tsr_changeset_revision is None:
                    return [ repository_to_install ], error_message
                else:
                    if tsr_changeset_revision == rti_changeset_revision:
                        return repository_dicts, error_message
        return repository_dicts, error_message
    # Get a list of repositories to test from the tool shed specified in the GALAXY_INSTALL_TEST_TOOL_SHED_URL
    # environment variable.
    log.debug( "The Tool Shed's API url...\n%s" % str( api_url ) )
    log.debug( "...retrieved %d repository revisions for testing." % len( repository_dicts ) )
    log.debug( "Repository revisions for testing:" )
    for repository_dict in repository_dicts:
        name = str( repository_dict.get( 'name', None ) )
        owner = str( repository_dict.get( 'owner', None ) )
        changeset_revision = str( repository_dict.get( 'changeset_revision', None ) )
        log.debug( "Revision %s of repository %s owned by %s" % ( changeset_revision, name, owner ) )
    return repository_dicts, error_message

def get_static_settings():
    """
    Return a dictionary of the settings necessary for a Galaxy application to be wrapped in the static
    middleware.  This mainly consists of the file system locations of url-mapped static resources.
    """
    cwd = os.getcwd()
    static_dir = os.path.join( cwd, 'static' )
    #TODO: these should be copied from universe_wsgi.ini
    #TODO: static_enabled needed here?
    return dict( static_enabled = True,
                 static_cache_time = 360,
                 static_dir = static_dir,
                 static_images_dir = os.path.join( static_dir, 'images', '' ),
                 static_favicon_dir = os.path.join( static_dir, 'favicon.ico' ),
                 static_scripts_dir = os.path.join( static_dir, 'scripts', '' ),
                 static_style_dir = os.path.join( static_dir, 'june_2007_style', 'blue' ),
                 static_robots_txt = os.path.join( static_dir, 'robots.txt' ) )

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

def get_tool_test_results_dicts( tool_shed_url, encoded_repository_metadata_id ):
    """
    Return the list of dictionaries contained in the Tool Shed's repository_metadata.tool_test_results
    column via the Tool Shed API.
    """
    error_message = ''
    parts = [ 'api', 'repository_revisions', encoded_repository_metadata_id ]
    api_url = get_api_url( base=tool_shed_url, parts=parts )
    repository_metadata, error_message = json_from_url( api_url )
    if error_message:
        return None, error_message
    # The tool_test_results used to be stored as a single dictionary rather than a list, but we currently
    # return a list.
    tool_test_results = listify( repository_metadata.get( 'tool_test_results', [] ) )
    return tool_test_results, error_message

def get_webapp_global_conf():
    """Return the global_conf dictionary sent as the first argument to app_factory."""
    global_conf = {}
    if STATIC_ENABLED:
        global_conf.update( get_static_settings() )
    return global_conf

def handle_missing_dependencies( app, repository, missing_tool_dependencies, repository_dict,
                                 tool_test_results_dicts, tool_test_results_dict, results_dict ):
    """Handle missing repository or tool dependencies for an installed repository."""
    # If a tool dependency fails to install correctly, this should be considered an installation error,
    # and functional tests should be skipped, since the tool dependency needs to be correctly installed
    # for the test to be considered reliable.
    log.debug( 'The following dependencies of this repository are missing, so skipping functional tests.' )
    # In keeping with the standard display layout, add the error message to the dict for each tool individually.
    for dependency in repository.missing_tool_dependencies:
        name = str( dependency.name )
        type = str( dependency.type )
        version = str( dependency.version )
        error_message = unicodify( dependency.error_message )
        log.debug( 'Missing tool dependency %s of type %s version %s: %s' % ( name, type, version, error_message ) )
        test_result = dict( type=dependency.type,
                            name=dependency.name,
                            version=dependency.version,
                            error_message=dependency.error_message )
        tool_test_results_dict[ 'installation_errors' ][ 'tool_dependencies' ].append( test_result )
    for dependency in repository.missing_repository_dependencies:
        name = str( dependency.name )
        owner = str( dependency.owner )
        changeset_revision = str( dependency.changeset_revision )
        error_message = unicodify( dependency.error_message )
        log.debug( 'Missing repository dependency %s changeset revision %s owned by %s: %s' % \
            ( name, changeset_revision, owner, error_message ) )
        test_result = dict( tool_shed=dependency.tool_shed,
                            name=dependency.name,
                            owner=dependency.owner,
                            changeset_revision=dependency.changeset_revision,
                            error_message=dependency.error_message )
        tool_test_results_dict[ 'installation_errors' ][ 'repository_dependencies' ].append( test_result )
    # Record the status of this repository in the tool shed.
    params = dict( tools_functionally_correct=False,
                   do_not_test=False,
                   test_install_error=True )
    # TODO: do something useful with response_dict
    response_dict = register_test_result( galaxy_tool_shed_url,
                                          tool_test_results_dicts,
                                          tool_test_results_dict,
                                          repository_dict,
                                          params )
    # Since this repository is missing components, we do not want to test it, so deactivate it or uninstall it.
    # The deactivate flag is set to True if the environment variable GALAXY_INSTALL_TEST_KEEP_TOOL_DEPENDENCIES
    # is set to 'true'. 
    deactivate = asbool( os.environ.get( 'GALAXY_INSTALL_TEST_KEEP_TOOL_DEPENDENCIES', False ) )
    if deactivate:
        for missing_tool_dependency in missing_tool_dependencies:
            uninstall_tool_dependency( app, missing_tool_dependency )
        # We are deactivating this repository and all of its repository dependencies.
        deactivate_repository( app, repository_dict )
    else:
        # We are uninstalling this repository and all of its repository dependencies.
        uninstall_repository( app, repository_dict )
        results_dict[ 'repositories_failed_install' ].append( dict( name=str( repository.name ),
                                                                    owner=str( repository.owner ),
                                                                    changeset_revision=str( repository.changeset_revision ) ) )
        # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
        test_toolbox.toolbox = app.toolbox
    return results_dict

def initialize_results_dict():
    # Initialize a dictionary for the summary that will be printed to stdout.
    results_dict = {}
    results_dict[ 'total_repositories_tested' ] = 0
    results_dict[ 'all_tests_passed' ] = []
    results_dict[ 'at_least_one_test_failed' ] = []
    results_dict[ 'repositories_failed_install' ] = []
    return results_dict

def install_repository( app, repository_dict ):
    """Install a repository defined by the received repository_dict from the tool shed into Galaxy."""
    name = str( repository_dict[ 'name' ] )
    owner = str( repository_dict[ 'owner' ] )
    changeset_revision = str( repository_dict[ 'changeset_revision' ] )
    error_message = ''
    repository = None
    log.debug( "Installing revision %s of repository %s owned by %s." % ( changeset_revision, name, owner ) )
    # Explicitly clear tests from twill's test environment.
    remove_generated_tests( app )
    # Use the repository information dictionary to generate an install method that will install the repository into the
    # embedded Galaxy application, with tool dependencies and repository dependencies, if any.
    test_install_repositories.generate_install_method( repository_dict )
    # Configure nose to run the install method as a test.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the configured install method as a test. This method uses the embedded Galaxy application's web interface to
    # install the specified repository with tool and repository dependencies also selected for installation.
    result, _ = run_tests( test_config )
    try:
        repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
    except Exception, e:
        error_message = 'Error getting revision %s of repository %s owned by %s: %s' % ( changeset_revision, name, owner, str( e ) )
        log.exception( error_message )
    return repository, error_message

def install_and_test_repositories( app, galaxy_shed_tools_dict, galaxy_shed_tool_conf_file ):
    results_dict = initialize_results_dict()
    error_message = ''
    # Allow the option to keep or delete tool dependencies when a repository has been tested.
    deactivate = asbool( os.environ.get( 'GALAXY_INSTALL_TEST_KEEP_TOOL_DEPENDENCIES', False ) )
    # Initialize a dictionary for the summary that will be printed to stdout.
    total_repositories_tested = results_dict[ 'total_repositories_tested' ]
    repositories_to_install, error_message = get_repositories_to_install( galaxy_tool_shed_url )
    if error_message:
        return None, error_message
    # Handle repositories not to be tested.
    if os.path.exists( exclude_list_file ):
        # Entries in the exclude_list look something like this.
        # { 'reason': The default reason or the reason specified in this section,
        #   'repositories':
        #         [( name, owner, changeset revision if changeset revision else None ),
        #          ( name, owner, changeset revision if changeset revision else None )] }
        # If changeset revision is None, that means the entire repository is excluded from testing, otherwise only the specified
        # revision should be skipped.
        # We are testing deprecated repositories because it is possible that a deprecated repository contains valid tools that
        # someone has previously installed. Deleted repositories have never been installed, so should not be tested. If they are
        # undeleted, this script will then test them the next time it runs. We don't need to check if a repository has been deleted
        # here because our call to the Tool Shed API filters by downloadable='true', in which case deleted will always be False.
        log.debug( 'Loading the list of repositories excluded from testing from the file %s...', exclude_list_file )
        exclude_list = parse_exclude_list( exclude_list_file )
    else:
        exclude_list = []
    # Generate a test method that will use Twill to install each repository into the embedded Galaxy application that was
    # started up, installing repository and tool dependencies. Upon successful installation, generate a test case for each
    # functional test defined for each tool in the repository and execute the test cases. Record the result of the tests.
    # The traceback and captured output of the tool that was run will be recored for test failures.  After all tests have
    # completed, the repository is uninstalled, so test cases don't interfere with the next repository's functional tests.
    for repository_dict in repositories_to_install:
        # Each repository_dict looks something like:
        # { "changeset_revision": "13fa22a258b5",
        #   "contents_url": "/api/repositories/529fd61ab1c6cc36/contents",
        #   "deleted": false,
        #   "deprecated": false,
        #   "description": "Convert column case.",
        #   "downloadable": true,
        #   "id": "529fd61ab1c6cc36",
        #   "long_description": "This tool takes the specified columns and converts them to uppercase or lowercase.",
        #   "malicious": false,
        #   "name": "change_case",
        #   "owner": "test",
        #   "private": false,
        #   "repository_id": "529fd61ab1c6cc36",
        #   "times_downloaded": 0,
        #   "tool_shed_url": "http://toolshed.local:10001",
        #   "url": "/api/repository_revisions/529fd61ab1c6cc36",
        #   "user_id": "529fd61ab1c6cc36" }
        encoded_repository_metadata_id = repository_dict.get( 'id', None )
        # Add the URL for the tool shed we're installing from, so the automated installation methods go to the right place.
        repository_dict[ 'tool_shed_url' ] = galaxy_tool_shed_url
        # Get the name and owner out of the repository info dict.
        name = str( repository_dict[ 'name' ] )
        owner = str( repository_dict[ 'owner' ] )
        changeset_revision = str( repository_dict[ 'changeset_revision' ] )
        log.debug( "Processing revision %s of repository %s owned by %s..." % ( changeset_revision, name, owner ) )
        repository_identifier_dict = dict( name=name, owner=owner, changeset_revision=changeset_revision )
        # Retrieve the stored list of tool_test_results_dicts.
        tool_test_results_dicts, error_message = get_tool_test_results_dicts( galaxy_tool_shed_url, encoded_repository_metadata_id )
        if error_message:
            log.debug( error_message )
        else:
            if tool_test_results_dicts:
                # Inspect the tool_test_results_dict for the last test run to make sure it contains only a test_environment
                # entry.  If it contains more entries, then the script ~/tool_shed/api/check_repositories_for_functional_tests.py
                # was not executed in preparation for this script's execution, so we'll just create an empty dictionary.
                tool_test_results_dict = tool_test_results_dicts[ 0 ]
                if len( tool_test_results_dict ) <= 1:
                    # We can re-use the mostly empty tool_test_results_dict for this run because it is either empty or it contains only
                    # a test_environment entry.  If we use it we need to temporarily eliminate it from the list of tool_test_results_dicts
                    # since it will be re-inserted later.
                    tool_test_results_dict = tool_test_results_dicts.pop( 0 )
                elif len( tool_test_results_dict ) == 2 and \
                    'test_environment' in tool_test_results_dict and 'missing_test_components' in tool_test_results_dict:
                    # We can re-use tool_test_results_dict if its only entries are "test_environment" and "missing_test_components".
                    # In this case, some tools are missing tests components while others are not.
                    tool_test_results_dict = tool_test_results_dicts.pop( 0 )
                else:
                    # The latest tool_test_results_dict has been populated with the results of a test run, so it cannot be used.
                    tool_test_results_dict = {}
            else:
                # Create a new dictionary for this test test run, 
                tool_test_results_dict = {}
            # See if this repository should be skipped for any reason.
            this_repository_is_in_the_exclude_list = False
            skip_reason = None
            for exclude_dict in exclude_list:
                reason = exclude_dict[ 'reason' ]
                exclude_repositories = exclude_dict[ 'repositories' ]
                if ( name, owner, changeset_revision ) in exclude_repositories or ( name, owner, None ) in exclude_repositories:
                    this_repository_is_in_the_exclude_list = True
                    skip_reason = reason
                    break
            if this_repository_is_in_the_exclude_list:
                tool_test_results_dict[ 'not_tested' ] = dict( reason=skip_reason )
                params = dict( tools_functionally_correct=False,
                               do_not_test=False )
                # TODO: do something useful with response_dict
                response_dict = register_test_result( galaxy_tool_shed_url, tool_test_results_dicts, tool_test_results_dict, repository_dict, params )
                log.debug( "Not testing revision %s of repository %s owned by %s because it is in the exclude list for this test run." % \
                           ( changeset_revision, name, owner ) )
            else:
                test_environment_dict = tool_test_results_dict.get( 'test_environment', {} )
                if len( test_environment_dict ) == 0:
                    # Set information about the tool shed to nothing since we cannot currently determine it from here.
                    # We could eventually add an API method...
                    test_environment_dict = dict( tool_shed_database_version='',
                                                  tool_shed_mercurial_version='',
                                                  tool_shed_revision='' )
                # Add the current time as the approximate time that this test run occurs.  A similar value will also be
                # set to the repository_metadata.time_last_tested column, but we also store it here because the Tool Shed
                # may be configured to store multiple test run results, so each must be associated with a time stamp.
                now = time.strftime( "%Y-%m-%d %H:%M:%S" )
                # Add information about the current platform.
                test_environment_dict[ 'time_tested' ] = now
                test_environment_dict[ 'python_version' ] = platform.python_version()
                test_environment_dict[ 'architecture' ] = platform.machine()
                operating_system, hostname, operating_system_version, uname, arch, processor = platform.uname()
                test_environment_dict[ 'system' ] = '%s %s' % ( operating_system, operating_system_version )
                # Add information about the current Galaxy environment.
                test_environment_dict[ 'galaxy_database_version' ] = get_database_version( app )
                test_environment_dict[ 'galaxy_revision' ] = get_repository_current_revision( os.getcwd() )
                # Initialize and populate the tool_test_results_dict.
                tool_test_results_dict[ 'test_environment' ] = test_environment_dict
                tool_test_results_dict[ 'passed_tests' ] = []
                tool_test_results_dict[ 'failed_tests' ] = []
                tool_test_results_dict[ 'installation_errors' ] = dict( current_repository=[], repository_dependencies=[], tool_dependencies=[] )
                # Proceed with installing repositories and testing contained tools.
                repository, error_message = install_repository( app, repository_dict )
                if error_message:
                    tool_test_results_dict[ 'installation_errors' ][ 'current_repository' ] = error_message
                    # Even if the repository failed to install, execute the uninstall method, in case a dependency did succeed.
                    log.debug( 'Attempting to uninstall repository %s owned by %s.' % ( name, owner ) )
                    try:
                        repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
                    except Exception, e:
                        error_message = 'Unable to find installed repository %s owned by %s: %s.' % ( name, owner, str( e ) )
                        log.exception( error_message )
                    test_result = dict( tool_shed=galaxy_tool_shed_url,
                                        name=name,
                                        owner=owner,
                                        changeset_revision=changeset_revision,
                                        error_message=error_message )
                    tool_test_results_dict[ 'installation_errors' ][ 'repository_dependencies' ].append( test_result )
                    params = dict( tools_functionally_correct=False,
                                   test_install_error=True,
                                   do_not_test=False )
                    # TODO: do something useful with response_dict
                    response_dict = register_test_result( galaxy_tool_shed_url,
                                                          tool_test_results_dicts,
                                                          tool_test_results_dict,
                                                          repository_dict,
                                                          params )
                    try:
                        if deactivate:
                            # We are deactivating this repository and all of its repository dependencies.
                            deactivate_repository( app, repository_dict )
                        else:
                            # We are uninstalling this repository and all of its repository dependencies.
                            uninstall_repository( app, repository_dict )
                    except:
                        log.exception( 'Encountered error attempting to deactivate or uninstall %s.', str( repository_dict[ 'name' ] ) )
                    results_dict[ 'repositories_failed_install' ].append( repository_identifier_dict )
                    log.debug( 'Repository %s failed to install correctly.' % str( name ) )
                else:
                    # Configure and run functional tests for this repository. This is equivalent to sh run_functional_tests.sh -installed
                    remove_install_tests()
                    log.debug( 'Installation of %s succeeded, running all defined functional tests.' % str( repository.name ) )
                    # Generate the shed_tools_dict that specifies the location of test data contained within this repository. If the repository
                    # does not have a test-data directory, this will return has_test_data = False, and we will set the do_not_test flag to True,
                    # and the tools_functionally_correct flag to False, as well as updating tool_test_results.
                    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( {} ) )
                    has_test_data, shed_tools_dict = parse_tool_panel_config( galaxy_shed_tool_conf_file,
                                                                              from_json_string( file( galaxy_shed_tools_dict, 'r' ).read() ) )
                    # Add an empty 'missing_test_results' entry if it is missing from the tool_test_results_dict.  The 
                    # ~/tool_shed/scripts/check_repositories_for_functional_tests.py will have entered information in the
                    # 'missing_test_components' entry of the tool_test_results_dict dictionary for repositories that are
                    # missing test components.
                    if 'missing_test_components' not in tool_test_results_dict:
                        tool_test_results_dict[ 'missing_test_components' ] = []
                    missing_tool_dependencies = get_missing_tool_dependencies( repository )
                    if missing_tool_dependencies or repository.missing_repository_dependencies:
                        results_dict = handle_missing_dependencies( app,
                                                                    repository,
                                                                    missing_tool_dependencies,
                                                                    repository_dict,
                                                                    tool_test_results_dicts,
                                                                    tool_test_results_dict,
                                                                    results_dict )
                    else:
                        # If the repository has a test-data directory we write the generated shed_tools_dict to a file, so the functional
                        # test framework can find it.
                        file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( shed_tools_dict ) )
                        log.debug( 'Saved generated shed_tools_dict to %s\nContents: %s' % ( str( galaxy_shed_tools_dict ), str( shed_tools_dict ) ) )
                        try:
                            results_dict = test_repository_tools( app,
                                                                  repository,
                                                                  repository_dict,
                                                                  tool_test_results_dicts,
                                                                  tool_test_results_dict,
                                                                  results_dict )
                        except Exception, e:
                            exception_message = 'Error executing tests for repository %s: %s' % ( name, str( e ) )
                            log.exception( exception_message )
                            tool_test_results_dict[ 'failed_tests' ].append( exception_message )
                            # Record the status of this repository in the tool shed.
                            params = dict( tools_functionally_correct=False,
                                           do_not_test=False,
                                           test_install_error=False )
                            # TODO: do something useful with response_dict
                            response_dict = register_test_result( galaxy_tool_shed_url,
                                                                  tool_test_results_dicts,
                                                                  tool_test_results_dict,
                                                                  repository_dict,
                                                                  params )
                            results_dict[ 'at_least_one_test_failed' ].append( repository_identifier_dict )
                        total_repositories_tested += 1
    results_dict[ 'total_repositories_tested' ] = total_repositories_tested
    return results_dict, error_message

def is_latest_downloadable_revision( url, repository_dict ):
    latest_revision = get_latest_downloadable_changeset_revision( url, name=repository_dict[ 'name' ], owner=repository_dict[ 'owner' ] )
    return str( repository_dict[ 'changeset_revision' ] ) == str( latest_revision )

def json_from_url( url ):
    error_message = ''
    url_handle = urllib.urlopen( url )
    url_contents = url_handle.read()
    try:
        parsed_json = from_json_string( url_contents )
    except Exception, e:
        error_message = str( url_contents )
        log.exception( 'Error parsing JSON data in json_from_url(): %s.' % str( e ) )
        return None, error_message
    return parsed_json, error_message

def main():
    if tool_shed_api_key is None:
        # If the tool shed URL specified in any dict is not present in the tool_sheds_conf.xml, the installation will fail.
        log.debug( 'Cannot proceed without a valid tool shed API key set in the enviroment variable GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY.' )
        return 1
    if galaxy_tool_shed_url is None:
        log.debug( 'Cannot proceed without a valid Tool Shed base URL set in the environment variable GALAXY_INSTALL_TEST_TOOL_SHED_URL.' )
        return 1
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST', default_galaxy_test_host )
    # Set the GALAXY_INSTALL_TEST_HOST variable so that Twill will have the Galaxy url to which to
    # install repositories.
    os.environ[ 'GALAXY_INSTALL_TEST_HOST' ] = galaxy_test_host
    # Set the GALAXY_TEST_HOST environment variable so that the toolbox tests will have the Galaxy url
    # on which to to run tool functional tests.
    os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
    galaxy_test_port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT', str( default_galaxy_test_port_max ) )
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
    shed_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF',
                                                     os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_data_table_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF',
                                                       tool_data_table_conf )
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
    galaxy_shed_tools_dict = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DICT_FILE',
                                             os.path.join( galaxy_test_tmp_dir, 'shed_tool_dict' ) )
    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( {} ) )
    # Set the GALAXY_TOOL_SHED_TEST_FILE environment variable to the path of the shed_tools_dict file so that
    # test.base.twilltestcase.setUp will find and parse it properly.
    os.environ[ 'GALAXY_TOOL_SHED_TEST_FILE' ] = galaxy_shed_tools_dict
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
    galaxy_shed_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir, prefix='shed_tools' )
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
    kwargs = {}
    for dir in [ galaxy_test_tmp_dir ]:
        try:
            os.makedirs( dir )
        except OSError:
            pass
    print "Database connection: ", database_connection
    # Generate the shed_tool_data_table_conf.xml file.
    file( shed_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF' ] = shed_tool_data_table_conf_file
    # ---- Start up a Galaxy instance ------------------------------------------------------
    # Generate the tool_conf.xml file.
    file( galaxy_tool_conf_file, 'w' ).write( tool_conf_xml )
    # Generate the job_conf.xml file.
    file( galaxy_job_conf_file, 'w' ).write( job_conf_xml )
    # Generate the tool_sheds_conf.xml file, but only if a the user has not specified an existing one in the environment.
    if 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF' not in os.environ:
        file( galaxy_tool_sheds_conf_file, 'w' ).write( tool_sheds_conf_xml )
    # Generate the shed_tool_conf.xml file.
    tool_conf_template_parser = string.Template( shed_tool_conf_xml_template )
    shed_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_shed_tool_path )
    file( galaxy_shed_tool_conf_file, 'w' ).write( shed_tool_conf_xml )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF' ] = galaxy_shed_tool_conf_file
    # Generate the migrated_tool_conf.xml file.
    migrated_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_migrated_tool_path )
    file( galaxy_migrated_tool_conf_file, 'w' ).write( migrated_tool_conf_xml )
    # Write the embedded web application's specific configuration to a temporary file. This is necessary in order for
    # the external metadata script to find the right datasets.
    kwargs = dict( admin_users = 'test@bx.psu.edu',
                   master_api_key = default_galaxy_master_api_key,
                   allow_user_creation = True,
                   allow_user_deletion = True,
                   allow_library_path_paste = True,
                   database_connection = database_connection,
                   datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                   file_path = galaxy_file_path,
                   id_secret = galaxy_encode_secret,
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
        # Write a temporary file, based on universe_wsgi.ini.sample, using the configuration options defined above.
        generate_config_file( 'universe_wsgi.ini.sample', galaxy_config_file, config_items )
    kwargs[ 'tool_config_file' ] = [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ]
    # Set the global_conf[ '__file__' ] option to the location of the temporary .ini file, which gets passed to set_metadata.sh.
    kwargs[ 'global_conf' ] = get_webapp_global_conf()
    kwargs[ 'global_conf' ][ '__file__' ] = galaxy_config_file
    # ---- Build Galaxy Application --------------------------------------------------
    if not database_connection.startswith( 'sqlite://' ):
        kwargs[ 'database_engine_option_max_overflow' ] = '20'
        kwargs[ 'database_engine_option_pool_size' ] = '10'
    kwargs[ 'config_file' ] = galaxy_config_file
    app = UniverseApplication( **kwargs )
    database_contexts.galaxy_context = app.model.context
    database_contexts.install_context = app.install_model.context
    global test_toolbox
    import functional.test_toolbox as imported_test_toolbox
    test_toolbox = imported_test_toolbox

    log.debug( "Embedded Galaxy application started..." )
    # ---- Run galaxy webserver ------------------------------------------------------
    server = None
    global_conf = get_webapp_global_conf()
    global_conf[ 'database_file' ] = database_connection
    webapp = buildapp.app_factory( global_conf,
                                   use_translogger=False,
                                   static_enabled=STATIC_ENABLED,
                                   app=app )
    # Serve the app on a specified or random port.
    if galaxy_test_port is not None:
        server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                galaxy_test_port = str( random.randint( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
                log.debug( "Attempting to serve app on randomly chosen port: %s", galaxy_test_port )
                server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
                break
            except socket.error, e:
                if e[0] == 98:
                    continue
                raise
        else:
            raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % \
                             ( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
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
    log.debug( "Repositories will be installed from the tool shed at %s" % str( galaxy_tool_shed_url ) )
    success = False
    # If a tool_data_table_conf.test.xml file was found, add the entries from it into the app's tool data tables.
    if additional_tool_data_tables:
        app.tool_data_tables.add_new_entries_from_config_file( config_filename=additional_tool_data_tables,
                                                               tool_data_path=additional_tool_data_path,
                                                               shed_tool_data_table_config=None,
                                                               persist=False )
    now = time.strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - running repository installation and testing script." % now
    print "####################################################################################"
    results_dict, error_message = install_and_test_repositories( app, galaxy_shed_tools_dict, galaxy_shed_tool_conf_file )
    if error_message:
        log.debug( error_message )
    else:
        total_repositories_tested = results_dict[ 'total_repositories_tested' ]
        all_tests_passed = results_dict[ 'all_tests_passed' ]
        at_least_one_test_failed = results_dict[ 'at_least_one_test_failed' ]
        repositories_failed_install = results_dict[ 'repositories_failed_install' ]
        now = time.strftime( "%Y-%m-%d %H:%M:%S" )
        print "####################################################################################"
        print "# %s - repository installation and testing script completed." % now
        print "# Repository revisions tested: %s" % str( total_repositories_tested )
        if not can_update_tool_shed:
            print "# This run will not update the Tool Shed database."
        if total_repositories_tested > 0:
            if all_tests_passed:
                print '# ----------------------------------------------------------------------------------'
                print "# %d repositories successfully passed all functional tests:" % len( all_tests_passed )
                show_summary_output( all_tests_passed )
            if at_least_one_test_failed:
                print '# ----------------------------------------------------------------------------------'
                print "# %d repositories failed at least 1 functional test:" % len( at_least_one_test_failed )
                show_summary_output( at_least_one_test_failed )
            if repositories_failed_install:
                # Set success to False so that the return code will not be 0.
                success = False
                print '# ----------------------------------------------------------------------------------'
                print "# %d repositories have installation errors:" % len( repositories_failed_install )
                show_summary_output( repositories_failed_install )
            else:
                success = True
        else:
            success = True
        print "####################################################################################"
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
    # Normally the value of 'success' would determine whether this test suite is marked as passed or failed
    # in the automated buildbot framework. However, due to the procedure used here we only want to report
    # failure if a repository fails to install correctly, so we have overriden the value of 'success' here
    # based on what actions the script has executed.
    if success:
        return 0
    else:
        return 1

def parse_exclude_list( xml_filename ):
    """Return a list of repositories to exclude from testing."""
    # This method should return a list with the following structure:
    # [{ 'reason': The default reason or the reason specified in this section,
    #    'repositories': [( name, owner, changeset revision if changeset revision else None ),
    #                     ( name, owner, changeset revision if changeset revision else None )]}]
    exclude_list = []
    exclude_verbose = []
    xml_tree, error_message = parse_xml( xml_filename )
    if error_message:
        log.debug( 'The xml document %s defining the exclude list is invalid, so no repositories will be excluded from testing: %s' % \
            ( str( xml_filename ), str( error_message ) ) )
        return exclude_list
    tool_sheds = xml_tree.findall( 'repositories' )
    xml_element = []
    exclude_count = 0
    for tool_shed in tool_sheds:
        if galaxy_tool_shed_url != tool_shed.attrib[ 'tool_shed' ]:
            continue
        else:
            xml_element = tool_shed
    for reason_section in xml_element:
        reason_text = reason_section.find( 'text' ).text
        repositories = reason_section.findall( 'repository' )
        exclude_dict = dict( reason=reason_text, repositories=[] )
        for repository in repositories:
            repository_tuple = get_repository_tuple_from_elem( repository )
            if repository_tuple not in exclude_dict[ 'repositories' ]:
                exclude_verbose.append( repository_tuple )
                exclude_count += 1
                exclude_dict[ 'repositories' ].append( repository_tuple )
        exclude_list.append( exclude_dict )
    log.debug( 'The xml document %s containing the exclude list defines the following %s repositories to be excluded from testing...' % \
        ( str( xml_filename ), str( exclude_count ) ) )
    #if '-list_repositories' in sys.argv:
    for name, owner, changeset_revision in exclude_verbose:
        if changeset_revision:
            log.debug( 'Repository %s owned by %s, changeset revision %s.' % ( str( name ), str( owner ), str( changeset_revision ) ) )
        else:
            log.debug( 'Repository %s owned by %s, all revisions.' % ( str( name ), str( owner ) ) )
    return exclude_list

def register_test_result( url, tool_test_results_dicts, tool_test_results_dict, repository_dict, params ):
    """
    Update the repository metadata tool_test_results and appropriate flags using the Tool SHed API.  This method
    updates tool_test_results with the relevant data, sets the do_not_test and tools_functionally correct flags
    to the appropriate values and updates the time_last_tested field to the value of the received time_tested.
    """
    if can_update_tool_shed:
        metadata_revision_id = repository_dict.get( 'id', None )
        if metadata_revision_id is not None:
            tool_test_results_dicts.insert( 0, tool_test_results_dict )
            params[ 'tool_test_results' ] = tool_test_results_dicts
            # Set the time_last_tested entry so that the repository_metadata.time_last_tested will be set in the tool shed.
            params[ 'time_last_tested' ] = 'This entry will result in this value being set via the Tool Shed API.'
            url = '%s' % ( suc.url_join( galaxy_tool_shed_url,'api', 'repository_revisions', str( metadata_revision_id ) ) )
            try:
                return update( tool_shed_api_key, url, params, return_formatted=False )
            except Exception, e:
                log.exception( 'Error attempting to register test results: %s' % str( e ) )
                return {}
    else:
        return {}

def remove_generated_tests( app ):
    """
    Delete any configured tool functional tests from the test_toolbox.__dict__, otherwise nose will find them
    and try to re-run the tests after uninstalling the repository, which will cause false failure reports,
    since the test data has been deleted from disk by now.
    """
    tests_to_delete = []
    tools_to_delete = []
    global test_toolbox
    for key in test_toolbox.__dict__:
        if key.startswith( 'TestForTool_' ):
            log.debug( 'Tool test found in test_toolbox, deleting: %s' % str( key ) )
            # We can't delete this test just yet, we're still iterating over __dict__.
            tests_to_delete.append( key )
            tool_id = key.replace( 'TestForTool_', '' )
            for tool in app.toolbox.tools_by_id:
                if tool.replace( '_', ' ' ) == tool_id.replace( '_', ' ' ):
                    tools_to_delete.append( tool )
    for key in tests_to_delete:
        # Now delete the tests found in the previous loop.
        del test_toolbox.__dict__[ key ]
    for tool in tools_to_delete:
        del app.toolbox.tools_by_id[ tool ]

def remove_install_tests():
    """
    Delete any configured repository installation tests from the test_toolbox.__dict__, otherwise nose will find them
    and try to install the repository again while running tool functional tests.
    """
    tests_to_delete = []
    global test_toolbox
    # Push all the toolbox tests to module level
    for key in test_install_repositories.__dict__:
       if key.startswith( 'TestInstallRepository_' ):
            log.debug( 'Repository installation process found, deleting: %s' % str( key ) )
            # We can't delete this test just yet, we're still iterating over __dict__.
            tests_to_delete.append( key )
    for key in tests_to_delete:
        # Now delete the tests found in the previous loop.
        del test_install_repositories.__dict__[ key ]

def run_tests( test_config ):
    loader = nose.loader.TestLoader( config=test_config )
    test_config.plugins.addPlugin( ReportResults() )
    plug_loader = test_config.plugins.prepareTestLoader( loader )
    if plug_loader is not None:
        loader = plug_loader
    tests = loader.loadTestsFromNames( test_config.testNames )
    test_runner = nose.core.TextTestRunner( stream=test_config.stream,
                                            verbosity=test_config.verbosity,
                                            config=test_config )
    plug_runner = test_config.plugins.prepareTestRunner( test_runner )
    if plug_runner is not None:
        test_runner = plug_runner
    result = test_runner.run( tests )
    return result, test_config.plugins._plugins

def show_summary_output( repository_dicts ):
    # Group summary display by repository owner.
    repository_dicts_by_owner = {}
    for repository_dict in repository_dicts:
        name = str( repository_dict[ 'name' ] )
        owner = str( repository_dict[ 'owner' ] )
        changeset_revision = str( repository_dict[ 'changeset_revision' ] )
        if owner in repository_dicts_by_owner:
            repository_dicts_by_owner[ owner ].append( repository_dict )
        else:
            repository_dicts_by_owner[ owner ] = [ repository_dict ]
    # Display grouped summary.
    for owner, grouped_repository_dicts in repository_dicts_by_owner.items():
        print "# "
        for repository_dict in grouped_repository_dicts:
            name = repository_dict[ 'name' ]
            owner = repository_dict[ 'owner' ]
            changeset_revision = repository_dict[ 'changeset_revision' ]
            print "# Revision %s of repository %s owned by %s" % ( changeset_revision, name, owner )

def test_repository_tools( app, repository, repository_dict, tool_test_results_dicts, tool_test_results_dict, results_dict ):
    """Test tools contained in the received repository."""
    name = str( repository.name )
    owner = str( repository.owner )
    changeset_revision = str( repository.changeset_revision )
    repository_identifier_dict = dict( name=name, owner=owner, changeset_revision=changeset_revision )
    # Set the module-level variable 'toolbox', so that test.functional.test_toolbox will generate the appropriate test methods.
    test_toolbox.toolbox = app.toolbox
    # Generate the test methods for this installed repository. We need to pass in True here, or it will look
    # in $GALAXY_HOME/test-data for test data, which may result in missing or invalid test files.
    test_toolbox.build_tests( testing_shed_tools=True, master_api_key=default_galaxy_master_api_key )
    # Set up nose to run the generated functional tests.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the configured tests.
    result, test_plugins = run_tests( test_config )
    if result.wasSuccessful():
        # This repository's tools passed all functional tests.  Use the ReportResults nose plugin to get a list
        # of tests that passed.
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
        passed_repository_dict = repository_identifier_dict
        results_dict[ 'all_tests_passed' ].append( passed_repository_dict )
        params = dict( tools_functionally_correct=True,
                       do_not_test=False,
                       test_install_error=False )
        # Call the register_test_result() method to execute a PUT request to the repository_revisions API
        # controller with the status of the test. This also sets the do_not_test and tools_functionally
        # correct flags and updates the time_last_tested field to today's date.
        # TODO: do something useful with response_dict
        response_dict = register_test_result( galaxy_tool_shed_url,
                                              tool_test_results_dicts,
                                              tool_test_results_dict,
                                              repository_dict,
                                              params )
        log.debug( 'Revision %s of repository %s owned by %s installed and passed functional tests.' % \
            ( changeset_revision, name, owner ) )
    else:
        # The get_failed_test_dicts() method returns a list.
        failed_test_dicts = get_failed_test_dicts( result, from_tool_test=True )
        tool_test_results_dict[ 'failed_tests' ] = failed_test_dicts
        failed_repository_dict = repository_identifier_dict
        results_dict[ 'at_least_one_test_failed' ].append( failed_repository_dict )
        set_do_not_test = not is_latest_downloadable_revision( galaxy_tool_shed_url, repository_dict )
        params = dict( tools_functionally_correct=False,
                       test_install_error=False,
                       do_not_test=str( set_do_not_test ) )
        # TODO: do something useful with response_dict
        response_dict = register_test_result( galaxy_tool_shed_url,
                                              tool_test_results_dicts,
                                              tool_test_results_dict,
                                              repository_dict,
                                              params )
        log.debug( 'Revision %s of repository %s owned by %s installed successfully but did not pass functional tests.' % \
            ( changeset_revision, name, owner ) )
    # Run the uninstall method. This removes tool functional test methods from the test_toolbox module and uninstalls the
    # repository using Twill.
    deactivate = asbool( os.environ.get( 'GALAXY_INSTALL_TEST_KEEP_TOOL_DEPENDENCIES', False ) )
    if deactivate:
        log.debug( 'Deactivating changeset revision %s of repository %s' % ( str( changeset_revision ), str( name ) ) )
        # We are deactivating this repository and all of its repository dependencies.
        deactivate_repository( app, repository_dict )
    else:
        log.debug( 'Uninstalling changeset revision %s of repository %s' % ( str( changeset_revision ), str( name ) ) )
        # We are uninstalling this repository and all of its repository dependencies.
        uninstall_repository_and_repository_dependencies( app, repository_dict )
    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
    test_toolbox.toolbox = app.toolbox
    return results_dict

def uninstall_repository_and_repository_dependencies( app, repository_dict ):
    """Uninstall a repository and all of its repository dependencies."""
    # This method assumes that the repositor defined by the received repository_dict is not a repository
    # dependency of another repository.
    sa_session = app.install_model.context
    # Clean out any generated tests. This is necessary for Twill.
    remove_generated_tests( app )
    # The dict contains the only repository the app should have installed at this point.
    name = str( repository_dict[ 'name' ] )
    owner = str( repository_dict[ 'owner' ] )
    changeset_revision = str( repository_dict[ 'changeset_revision' ] )
    # Since this install and test framework uninstalls repositories immediately after installing and testing
    # them, the values of repository.installed_changeset_revision and repository.changeset_revision should be
    # the same.
    repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
    if repository.can_uninstall( app ):
        # A repository can be uninstalled only if no dependent repositories are installed.  So uninstallation order
        # id critical.  A repository is always uninstalled first, and the each of its dependencies is checked to see
        # if it can be uninstalled.
        uninstall_repository_dict = dict( name=name,
                                          owner=owner,
                                          changeset_revision=changeset_revision )
        log.debug( 'Revision %s of repository %s owned by %s selected for uninstallation.' % ( changeset_revision, name, owner ) )
        test_install_repositories.generate_uninstall_method( uninstall_repository_dict )
        # Set up nose to run the generated uninstall method as a functional test.
        test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
        test_config.configure( sys.argv )
        # Run the uninstall method. This method uses the Galaxy web interface to uninstall the previously installed
        # repository and all of its repository dependencies, deleting each of them from disk.
        result, _ = run_tests( test_config )
        success = result.wasSuccessful()
        if success:
            # Now that the repository is uninstalled we can attempt to uninstall each of its repository dependencies.
            # We have to do this through Twill in order to maintain app.toolbox and shed_tool_conf.xml in a state that
            # is valid for future tests.  Since some of the repository's repository dependencies may require other of
            # the repository's repository dependencies, we'll keep track of the repositories we've been able to unistall.
            processed_repository_dependency_ids = []
            while len( processed_repository_dependency_ids ) < len( repository.repository_dependencies ):
                for repository_dependency in repository.repository_dependencies:
                    if repository_dependency.id not in processed_repository_dependency_ids and repository_dependency.can_uninstall( app ):
                        processed_repository_dependency_ids.append( repository_dependency.id )
                        rd_name = str( repository_dependency.name )
                        rd_owner = str( repository_dependency.owner )
                        rd_changeset_revision = str( repository_dependency.changeset_revision )
                        uninstall_repository_dict = dict( name=rd_name,
                                                          owner=rd_owner,
                                                          changeset_revision=rd_changeset_revision )
                        log.debug( 'Revision %s of repository dependency %s owned by %s selected for uninstallation.' % \
                            ( rd_changeset_revision, rd_name, rd_owner ) )
                        # Generate a test method to uninstall the repository dependency through the embedded Galaxy application's
                        # web interface.
                        test_install_repositories.generate_uninstall_method( uninstall_repository_dict )
                        # Set up nose to run the generated uninstall method as a functional test.
                        test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
                        test_config.configure( sys.argv )
                        # Run the uninstall method.
                        result, _ = run_tests( test_config )
                        success = result.wasSuccessful()
                        if not success:
                            log.debug( 'Uninstallation of revision %s of repository %s owned by %s failed: %s' % \
                                ( rd_changeset_revision, rd_name, rd_owner, str( e ) ) )
        else:
            log.debug( 'Uninstallation of revision %s of repository %s owned by %s failed.' % ( changeset_revision, name, owner ) )
    else:
        log_reason_repository_cannot_be_uninstalled( app, repository )

def uninstall_tool_dependency( app, tool_dependency ):
    """Attempt to uninstall a tool dependency."""
    sa_session = app.install_model.context
    # Clean out any generated tests. This is necessary for Twill.
    tool_dependency_install_path = tool_dependency.installation_directory( app )
    uninstalled, error_message = tool_dependency_util.remove_tool_dependency( app, tool_dependency )
    if error_message:
        log.debug( 'There was an error attempting to remove directory: %s' % str( tool_dependency_install_path ) )
        log.debug( error_message )
    else:
        log.debug( 'Successfully removed tool dependency installation directory: %s' % str( tool_dependency_install_path ) )
    if not uninstalled or tool_dependency.status != app.model.ToolDependency.installation_status.UNINSTALLED:
        tool_dependency.status = app.model.ToolDependency.installation_status.UNINSTALLED
        sa_session.add( tool_dependency )
        sa_session.flush()
    if os.path.exists( tool_dependency_install_path ):
       log.debug( 'Uninstallation of tool dependency succeeded, but the installation path still exists on the filesystem. It is now being explicitly deleted.') 
       suc.remove_dir( tool_dependency_install_path )

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
