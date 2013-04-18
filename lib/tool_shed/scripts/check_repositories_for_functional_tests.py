#!/usr/bin/env python

import os, sys, logging, tempfile

new_path = [ os.path.join( os.getcwd(), "lib" ), os.path.join( os.getcwd(), "test" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

log = logging.getLogger()
log.setLevel( 10 )
log.addHandler( logging.StreamHandler( sys.stdout ) )

from galaxy import eggs
import pkg_resources  
eggs.require( "SQLAlchemy >= 0.4" )
eggs.require( 'mercurial' )
from mercurial import hg, ui, commands, __version__

import time, ConfigParser, shutil
from datetime import datetime, timedelta
from time import strftime
from optparse import OptionParser

import galaxy.webapps.tool_shed.config as tool_shed_config
import galaxy.webapps.tool_shed.model.mapping
import sqlalchemy as sa
from galaxy.model.orm import and_, not_
from galaxy.util.json import from_json_string, to_json_string
from galaxy.web import url_for
from galaxy.tools import parameters
from tool_shed.util.shed_util_common import clone_repository, get_configured_ui

from base.util import get_test_environment, get_database_version, get_repository_current_revision

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    '''Script that checks repositories to see if the tools contained within them have functional tests defined.'''
    parser = OptionParser()
    parser.add_option( "-i", "--info_only", action="store_true", dest="info_only", help="info about the requested action", default=False )
    parser.add_option( "-s", 
                       "--section", 
                       action="store", 
                       dest="section", 
                       default='server:main',
                       help="which .ini file section to extract the host and port from" )
    parser.add_option(
        "-v", "--verbose",
        action="count", dest="verbosity",
        default=1,
        help="Control the amount of detail in the log output.")
    parser.add_option(
        "--verbosity", action="store", dest="verbosity",
        metavar='VERBOSITY',
        type="int", help="Control the amount of detail in the log output. --verbosity=1 is "
        "the same as -v")
    ( options, args ) = parser.parse_args()
    try:
        ini_file = args[0]
    except IndexError:
        print "Usage: python %s <tool shed .ini file> [options]" % sys.argv[ 0 ]
        exit( 127 )
    config_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    config_parser.read( ini_file )
    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[key] = value
    config = tool_shed_config.Configuration( **config_dict )
    
    config_section = options.section
    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "#############################################################################"
    print "# %s - Checking repositories for tools with functional tests." % now
    print "# This tool shed is configured to listen on %s:%s." % ( config_parser.get( config_section, 'host' ), config_parser.get( config_section, 'port' ) )
    app = FlagRepositoriesApplication( config )
    
    if options.info_only:
        print "# Displaying info only ( --info_only )"
    if options.verbosity:
        print "# Displaying extra information ( --verbosity = %d )" % options.verbosity
    
    check_and_flag_repositories( app, info_only=options.info_only, verbosity=options.verbosity )

def check_and_flag_repositories( app, info_only=False, verbosity=1 ):
    '''
    This method will iterate through all records in the repository_metadata table, checking each one for tool metadata, 
    then checking the tool metadata for tests.
    Each tool's metadata should look something like:
    {
      "add_to_tool_panel": true,
      "description": "",
      "guid": "toolshed.url:9009/repos/owner/name/tool_id/1.2.3",
      "id": "tool_wrapper",
      "name": "Map with Tool Wrapper",
      "requirements": [],
      "tests": [
        {
          "inputs": [ [ "parameter", "value" ], [ "other_parameter", "other_value" ], ],
          "name": "Test-1",
          "outputs": [
            [
              "output_field_name",
              "output_file_name.bed"
            ]
          ],
          "required_files": [ '1.bed', '2.bed', '3.bed' ]
        }
      ],
      "tool_config": "database/community_files/000/repo_1/tool_wrapper.xml",
      "tool_type": "default",
      "version": "1.2.3",
      "version_string_cmd": null
    }
    
    If the "tests" attribute is missing or empty, this script will mark the metadata record (which is specific to a changeset revision of a repository)
    not to be tested. If each "tools" attribute has at least one valid "tests" entry, this script will do nothing, and leave it available for the install
    and test repositories script to process. If the tested changeset revision does not have a test-data directory, this script will also mark the revision
    not to be tested.
    
    If any error is encountered, the script will update the repository_metadata.tool_test_errors attribute following this structure:
    {
        "test_environment":
            {
                 "galaxy_revision": "9001:abcd1234",
                 "galaxy_database_version": "114",
                 "tool_shed_revision": "9001:abcd1234",
                 "tool_shed_mercurial_version": "2.3.1",
                 "tool_shed_database_version": "17",
                 "python_version": "2.7.2",
                 "architecture": "x86_64",
                 "system": "Darwin 12.2.0"
            },
        "test_errors":
            [
                {
                    "test_id": "The test ID, generated by twill",
                    "tool_id": "The tool ID that was tested",
                    "tool_version": "The tool version that was tested",
                    "stderr": "The output of the test, or a more detailed description of what was tested and what the error was."
                    "traceback": "The traceback, if any."
                },
            ]
         "passed_tests":
            [
                {
                    "test_id": "The test ID, generated by twill",
                    "tool_id": "The tool ID that was tested",
                    "tool_version": "The tool version that was tested",
                },
            ]
         "invalid_tests":
            [
                {
                    "tool_id": "The tool ID that does not have functional tests defined.",
                    "tool_version": "The version of the tool."
                    "tool_guid": "The guid of the tool."
                    "reason_test_is_invalid": "A short explanation of what is invalid.
                },
            ]
    }
    '''
    start = time.time()
    checked_repository_ids = []
    tool_count = 0
    has_tests = 0
    no_tests = 0
    no_tools = 0
    valid_revisions = 0
    invalid_revisions = 0
    # Get the list of metadata records to check for functional tests and test data. Limit this to records that have not been flagged do_not_test,
    # since there's no need to check them again if they won't be tested anyway. Also filter out changeset revisions that are not downloadable,
    # because it's redundant to test a revision that a user can't install.
    metadata_records_to_check = app.sa_session.query( app.model.RepositoryMetadata ) \
                                              .filter( and_( app.model.RepositoryMetadata.table.c.downloadable == True,
                                                             app.model.RepositoryMetadata.table.c.includes_tools == True,
                                                             app.model.RepositoryMetadata.table.c.do_not_test == False ) ) \
                                              .all()
    for metadata_record in metadata_records_to_check:
        # Initialize the repository_status dict with the test environment, but leave the test_errors empty. 
        repository_status = {}
        if metadata_record.tool_test_errors:
            repository_status = metadata_record.tool_test_errors
        # Clear any old invalid tests for this metadata revision, since this could lead to duplication of invalid test rows,
        # or tests incorrectly labeled as invalid.
        repository_status[ 'invalid_tests' ] = []
        if 'test_environment' in repository_status:
            repository_status[ 'test_environment' ] = get_test_environment( repository_status[ 'test_environment' ] )
        else:
            repository_status[ 'test_environment' ] = get_test_environment()
        repository_status[ 'test_environment' ][ 'tool_shed_database_version' ] = get_database_version( app )
        repository_status[ 'test_environment' ][ 'tool_shed_mercurial_version' ] = __version__.version
        repository_status[ 'test_environment' ][ 'tool_shed_revision' ] = get_repository_current_revision( os.getcwd() )
        name = metadata_record.repository.name
        owner = metadata_record.repository.user.username
        changeset_revision = str( metadata_record.changeset_revision )
        if metadata_record.repository.id not in checked_repository_ids:
            checked_repository_ids.append( metadata_record.repository.id )
        if verbosity >= 1:
            print '# -------------------------------------------------------------------------------------------'
            print '# Now checking revision %s of %s, owned by %s.' % ( changeset_revision,  name, owner ) 
        # If this changeset revision has no tools, we don't need to do anything here, the install and test script has a filter for returning
        # only repositories that contain tools.
        if 'tools' not in metadata_record.metadata:
            continue
        else:
            has_test_data = False
            # Clone the repository up to the changeset revision we're checking.
            repo_dir = metadata_record.repository.repo_path( app )
            repo = hg.repository( get_configured_ui(), repo_dir )
            work_dir = tempfile.mkdtemp()
            cloned_ok, error_message = clone_repository( repo_dir, work_dir, changeset_revision )
            if cloned_ok:
                # Iterate through all the directories in the cloned changeset revision and determine whether there's a
                # directory named test-data. If this directory is not present, update the metadata record for the changeset
                # revision we're checking.
                for root, dirs, files in os.walk( work_dir ):
                    if '.hg' in dirs:
                        dirs.remove( '.hg' )
                    if 'test-data' in dirs:
                        has_test_data = True
                        test_data_path = os.path.join( root, dirs[ dirs.index( 'test-data' ) ] )
                        break
            if verbosity >= 1:
                if not has_test_data:
                    print '# Test data directory missing in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                else:
                    print '# Test data directory found in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                print '# Checking for functional tests in changeset revision %s of %s, owned by %s.' % \
                    ( changeset_revision,  name, owner ) 
            # Loop through all the tools in this metadata record, checking each one for defined functional tests.
            for tool_metadata in metadata_record.metadata[ 'tools' ]:
                tool_count += 1
                tool_id = tool_metadata[ 'id' ]
                tool_version = tool_metadata[ 'version' ]
                tool_guid = tool_metadata[ 'guid' ]
                if verbosity >= 2:
                    print "# Checking tool ID '%s' in changeset revision %s of %s." % \
                        ( tool_id, changeset_revision, name ) 
                # If there are no tests, this tool should not be tested, since the tool functional tests only report failure if the test itself fails,
                # not if it's missing or undefined. Filtering out those repositories at this step will reduce the number of "false negatives" the
                # automated functional test framework produces.
                tool_has_tests = True
                if 'tests' not in tool_metadata or not tool_metadata[ 'tests' ]:
                    tool_has_tests = False
                    if verbosity >= 2:
                        print '# No functional tests defined for %s.' % tool_id
                    no_tests += 1
                else:
                    tool_has_tests = True
                    if verbosity >= 2:
                        print "# Tool ID '%s' in changeset revision %s of %s has one or more valid functional tests defined." % \
                            ( tool_id, changeset_revision, name ) 
                    has_tests += 1
                failure_reason = ''
                problem_found = False
                missing_test_files = []
                if tool_has_tests and has_test_data:
                    missing_test_files = check_for_missing_test_files( tool_metadata[ 'tests' ], test_data_path )
                    if missing_test_files:
                        if verbosity >= 2:
                            print "# Tool ID '%s' in changeset revision %s of %s is missing one or more required test files: %s" % \
                                ( tool_id, changeset_revision, name, ', '.join( missing_test_files ) ) 
                if not has_test_data:
                    failure_reason += 'Repository does not have a test-data directory. '
                    problem_found = True
                if not tool_has_tests:
                    failure_reason += 'Functional test definitions missing for %s. ' % tool_id
                    problem_found = True
                if missing_test_files:
                    failure_reason += 'One or more test files are missing for tool %s: %s' % ( tool_id, ', '.join( missing_test_files ) )
                    problem_found = True
                test_errors = dict( tool_id=tool_id, tool_version=tool_version, tool_guid=tool_guid,
                                    reason_test_is_invalid=failure_reason )
                # The repository_metadata.tool_test_errors attribute should always have the following structure:
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
                #     "test_errors":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
                #                 "traceback": "The captured traceback."
                #             },
                #         ]
                #      "passed_tests":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
                #             },
                #         ]
                #      "invalid_tests":
                #         [
                #             {
                #                 "tool_id": "The ID of the tool that does not have valid tests.",
                #                 "tool_version": "The version of the tool."
                #                 "tool_guid": "The guid of the tool."
                #                 "reason_test_is_invalid": "A short explanation of what is invalid."
                #             },
                #         ]
                # }
                # 
                # Optionally, "traceback" may be included in a test_errors dict, if it is relevant. No script should overwrite anything other
                # than the list relevant to what it is testing.
                # Only append this error dict if it hasn't already been added.
                if problem_found:
                    if test_errors not in repository_status[ 'invalid_tests' ]:
                        repository_status[ 'invalid_tests' ].append( test_errors )
            # Remove the cloned repository path. This has to be done after the check for required test files, for obvious reasons.
            if os.path.exists( work_dir ):
                shutil.rmtree( work_dir )
            if not repository_status[ 'invalid_tests' ]:
                valid_revisions += 1
                if verbosity >= 1:
                    print '# All tools have functional tests in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
            else:
                invalid_revisions += 1
                if verbosity >= 1:
                    print '# Some tools have problematic functional tests in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                    if verbosity >= 2:
                        for invalid_test in repository_status[ 'invalid_tests' ]:
                            if 'reason_test_is_invalid' in invalid_test:
                                print '# %s' % invalid_test[ 'reason_test_is_invalid' ]
            if not info_only:
                # If repository_status[ 'test_errors' ] is empty, no issues were found, and we can just update time_last_tested with the platform
                # on which this script was run.
                if repository_status[ 'invalid_tests' ]:
                    # If functional test definitions or test data are missing, set do_not_test = True if and only if:
                    # a) There are multiple downloadable revisions, and the revision being tested is not the most recent downloadable revision.
                    #    In this case, the revision will never be updated with correct data, and re-testing it would be redundant.
                    # b) There are one or more downloadable revisions, and the revision being tested is the most recent downloadable revision.
                    #    In this case, if the repository is updated with test data or functional tests, the downloadable changeset revision
                    #    that was tested will be replaced with the new changeset revision, which will be automatically tested.
                    if should_set_do_not_test_flag( app, metadata_record.repository, changeset_revision ):
                        metadata_record.do_not_test = True
                    metadata_record.tools_functionally_correct = False
                metadata_record.tool_test_errors = repository_status
                metadata_record.time_last_tested = datetime.utcnow()
                app.sa_session.add( metadata_record )
                app.sa_session.flush()
    stop = time.time()
    print '# -------------------------------------------------------------------------------------------'
    print '# Checked %d repositories with %d tools in %d changeset revisions.' % ( len( checked_repository_ids ), tool_count, len( metadata_records_to_check ) )
    print '# %d revisions found with functional tests and test data for all tools.' % valid_revisions
    print '# %d revisions found with one or more tools missing functional tests and/or test data.' % invalid_revisions
    print '# Found %d tools without functional tests.' % no_tests
    print '# Found %d tools with functional tests.' % has_tests
    if info_only:
        print '# Database not updated, info_only set.'
    print "# Elapsed time: ", stop - start
    print "#############################################################################" 

def get_repo_changelog_tuples( repo_path ):
    repo = hg.repository( ui.ui(), repo_path )
    changelog_tuples = []
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        changelog_tuples.append( ( ctx.rev(), str( ctx ) ) )
    return changelog_tuples

def check_for_missing_test_files( test_definition, test_data_path ):
    '''Process the tool's functional test definitions and check for each file specified as an input or output.'''
    missing_test_files = []
    required_test_files = []
    for test_dict in test_definition:
        for input_file in test_dict[ 'required_files' ]:
            if input_file not in required_test_files:
                required_test_files.append( input_file )
        for output in test_dict[ 'outputs' ]:
            fieldname, filename = output
            # In rare cases, the filename may be None. If that is the case, skip that output definition.
            if filename is None:
                continue
            if filename not in required_test_files:
                required_test_files.append( filename )
    # Make sure each specified file actually does exist in the test data path of the cloned repository.
    for required_file in required_test_files:
        required_file_full_path = os.path.join( test_data_path, required_file )
        if not os.path.exists( required_file_full_path ):
            missing_test_files.append( required_file )
    return missing_test_files

def is_most_recent_downloadable_revision( app, repository, changeset_revision, downloadable_revisions ):
    # Get a list of ( numeric revision, changeset hash ) tuples from the changelog.
    changelog = get_repo_changelog_tuples( repository.repo_path( app ) )
    latest_downloadable_revision = None
    for ctx_rev, changeset_hash in changelog:
        if changeset_hash in downloadable_revisions:
            # The last changeset hash in the changelog that is present in the list of downloadable revisions will always be the most
            # recent downloadable revision, since the changelog tuples are ordered from earliest to most recent.
            latest_downloadable_revision = changeset_hash
    if latest_downloadable_revision == changeset_revision:
        return True
    return False

def should_set_do_not_test_flag( app, repository, changeset_revision ):
    '''
    Returns True if:
    a) There are multiple downloadable revisions, and the provided changeset revision is not the most recent downloadable revision. In this case,
       the revision will never be updated with correct data, and re-testing it would be redundant.
    b) There are one or more downloadable revisions, and the provided changeset revision is the most recent downloadable revision. In this case, if 
       the repository is updated with test data or functional tests, the downloadable changeset revision that was tested will either be replaced
       with the new changeset revision, or a new downloadable changeset revision will be created, either of which will be automatically checked and
       flagged as appropriate. In the install and test script, this behavior is slightly different, since we do want to always run functional tests
       on the most recent downloadable changeset revision.
    '''
    metadata_records = app.sa_session.query( app.model.RepositoryMetadata ) \
                                     .filter( and_( app.model.RepositoryMetadata.table.c.downloadable == True,
                                                    app.model.RepositoryMetadata.table.c.repository_id == repository.id ) ) \
                                     .all()
    downloadable_revisions = [ metadata_record.changeset_revision for metadata_record in metadata_records ]
    is_latest_revision = is_most_recent_downloadable_revision( app, repository, changeset_revision, downloadable_revisions )
    if len( downloadable_revisions ) == 1:
        return True
    elif len( downloadable_revisions ) > 1 and is_latest_revision:
        return True
    elif len( downloadable_revisions ) > 1 and not is_latest_revision:
        return True
    else:
        return False
    
    
class FlagRepositoriesApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, config ):
        if config.database_connection is False:
            config.database_connection = "sqlite:///%s?isolation_level=IMMEDIATE" % config.database
        # Setup the database engine and ORM
        self.model = galaxy.webapps.tool_shed.model.mapping.init( config.file_path, config.database_connection, engine_options={}, create_tables=False )
        self.hgweb_config_manager = self.model.hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = config.hgweb_config_dir
        print "# Using configured hgweb.config file: ", self.hgweb_config_manager.hgweb_config
    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.model.context.current
    def shutdown( self ):
        pass

if __name__ == "__main__": main()
