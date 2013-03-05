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
pkg_resources.require( "SQLAlchemy >= 0.4" )
pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

import time, ConfigParser, shutil
from datetime import datetime, timedelta
from time import strftime
from optparse import OptionParser

import galaxy.webapps.tool_shed.config as tool_shed_config
import galaxy.webapps.tool_shed.model.mapping
import sqlalchemy as sa
from galaxy.model.orm import and_, not_, distinct
from galaxy.util.json import from_json_string, to_json_string
from galaxy.web import url_for
from tool_shed.util.shed_util_common import clone_repository, get_configured_ui

from base.util import get_test_environment

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    '''Script that checks repositories to see if the tools contained within them have functional tests defined.'''
    parser = OptionParser()
    parser.add_option( "-i", "--info_only", action="store_true", dest="info_only", help="info about the requested action", default=False )
    parser.add_option( "-v", "--verbose", action="store_true", dest="verbose", help="verbose mode, print the name, owner, and changeset revision of each repository", default=False )
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    config_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    config_parser.read( ini_file )
    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[key] = value
    config = tool_shed_config.Configuration( **config_dict )
    
    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "#############################################################################"
    print "# %s - Checking repositories for tools with functional tests." % now
    app = FlagRepositoriesApplication( config )
    
    if options.info_only:
        print "# Displaying info only ( --info_only )"
    if options.verbose:
        print "# Displaying extra information ( --verbose )"
    
    check_and_flag_repositories( app, info_only=options.info_only, verbose=options.verbose )

def check_and_flag_repositories( app, info_only=False, verbose=False ):
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
    
    If any error is encountered, the script will update the repository_metadata.tool_test_errors attribute with the following structure:
    {
        "test_environment":
            {
                 "python_version": "2.7.2",
                 "architecture": "x86_64",
                 "system": "Darwin 12.2.0"
            },
        "test_errors":
            [
                {
                    "test_id": "Something that will easily identify what the problem is",
                    "stdout": "The output of the test, or a more detailed description of what was tested and why it failed."
                },
            ]
    }
    '''
    start = time.time()
    repository_ids_to_check = []
    tool_count = 0
    has_tests = 0
    no_tests = 0
    no_tools = 0
    # Get the list of metadata records to check for functional tests and test data. Limit this to records that have not been flagged do_not_test
    # or tools_functionally_correct. Also filter out changeset revisions that are not downloadable, because it's redundant to test a revision that
    # a user can't install.
    metadata_records_to_check = app.sa_session.query( app.model.RepositoryMetadata ) \
                                              .filter( and_( app.model.RepositoryMetadata.table.c.downloadable == True,
                                                             app.model.RepositoryMetadata.table.c.do_not_test == False,
                                                             app.model.RepositoryMetadata.table.c.tools_functionally_correct == False ) ) \
                                              .all()
    for metadata_record in metadata_records_to_check:
        name = metadata_record.repository.name
        owner = metadata_record.repository.user.username
        changeset_revision = str( metadata_record.changeset_revision )
        repository_status = {}
        # If this changeset revision has no tools, we don't need to do anything here, the install and test script has a filter for returning
        # only repositories that contain tools.
        if 'tools' not in metadata_record.metadata:
            no_tools += 1
            continue
        else:
            # Initialize the repository_status dict with the test environment, but leave the test_errors empty. 
            repository_status[ 'test_environment' ] = get_test_environment()
            repository_status[ 'test_errors' ] = []
            # Loop through all the tools in this metadata record, checking each one for defined functional tests.
            for tool_metadata in metadata_record.metadata[ 'tools' ]:
                tool_count += 1
                tool_id = tool_metadata[ 'id' ]
                if verbose:
                    print '# Checking for functional tests in changeset revision %s of %s, tool ID %s.' % \
                        ( changeset_revision,  name, tool_id ) 
                # If there are no tests, this tool should not be tested, since the tool functional tests only report failure if the test itself fails,
                # not if it's missing or undefined. Filtering out those repositories at this step will reduce the number of "false negatives" the
                # automated functional test framework produces.
                if 'tests' not in tool_metadata or not tool_metadata[ 'tests' ]:
                    if verbose:
                        print '# No functional tests defined for %s.' % tool_id
                    if 'test_errors' not in repository_status:
                        repository_status[ 'test_errors' ] = []
                    test_id = 'Functional tests for %s' % tool_id
                    # The repository_metadata.tool_test_errors attribute should always have the following structure:
                    # {
                    #     "environment":
                    #         {
                    #              "python_version": "2.7.2",
                    #              "architecture": "x86_64",
                    #              "system": "Darwin 12.2.0"
                    #         },
                    #     "test_errors":
                    #         [
                    #             {
                    #                 "test_id": "Something that will easily identify what the problem is",
                    #                 "stdout": "The output of the test, or a more detailed description of what was tested and why it failed."
                    #             },
                    #         ]
                    # }
                    # Optionally, "stderr" and "traceback" may be included in a test_errors dict, if they are relevant.
                    test_errors = dict( test_id=test_id, 
                                        stdout='No functional tests defined in changeset revision %s of repository %s owned by %s.' % \
                                            ( changeset_revision, name, owner ) )
                    repository_status[ 'test_errors' ].append( test_errors )
                    no_tests += 1
                else:
                    has_tests += 1
            if verbose:
                if not repository_status[ 'test_errors' ]:
                    print '# All tools have functional tests in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                else:
                    print '# Some tools missing functional tests in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
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
                        break
            # Remove the cloned path.
            if os.path.exists( work_dir ):
                shutil.rmtree( work_dir )
            if not has_test_data:
                if verbose:
                    print '# Test data missing in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
                repository_status[ 'test_environment' ] = get_test_environment()
                test_id = 'Find functional test data for %s' % metadata_record.repository.name
                # The repository_metadata.tool_test_errors attribute should always have the following structure:
                # {
                #     "test_environment":
                #         {
                #              "python_version": "2.7.2",
                #              "architecture": "x86_64",
                #              "system": "Darwin 12.2.0"
                #         },
                #     "test_errors":
                #         [
                #             {
                #                 "test_id": "Something that will easily identify what the problem is",
                #                 "stdout": "The output of the test, or a more detailed description of what was tested and why it failed."
                #             },
                #         ]
                # }
                # Optionally, "stderr" and "traceback" may be included in a test_errors dict, if they are relevant.
                test_errors = dict( test_id=test_id, 
                                    stdout='No test data found for changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner ) )
                repository_status[ 'test_errors' ].append( test_errors )
            else:
                if verbose:
                    print '# Test data found in changeset revision %s of repository %s owned by %s.' % ( changeset_revision, name, owner )
            if not info_only:
                if repository_status[ 'test_errors' ]:
                    metadata_record.do_not_test = True
                    metadata_record.tools_functionally_correct = False
                metadata_record.tool_test_errors = to_json_string( repository_status )
                metadata_record.time_last_tested = datetime.utcnow()
                app.sa_session.add( metadata_record )
                app.sa_session.flush()
    stop = time.time()
    print '# Checked %d tools in %d changeset revisions.' % ( tool_count, len( metadata_records_to_check ) )
    print '# Found %d changeset revisions without tools.' % no_tools
    print '# Found %d tools without functional tests.' % no_tests
    print '# Found %d tools with functional tests.' % has_tests
    if info_only:
        print '# Database not updated, info_only set.'
    print "# Elapsed time: ", stop - start
    print "#############################################################################" 

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
