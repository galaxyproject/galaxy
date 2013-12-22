#!/usr/bin/env python

from datetime import datetime
from optparse import OptionParser
from time import strftime

import ConfigParser
import logging
import os
import shutil
import sys
import time
import tempfile

new_path = [ os.path.join( os.getcwd(), "lib" ), os.path.join( os.getcwd(), "test" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs
eggs.require( "SQLAlchemy >= 0.4" )
eggs.require( 'mercurial' )

from mercurial import __version__

import galaxy.webapps.tool_shed.config as tool_shed_config

from install_and_test_tool_shed_repositories.base.util import get_database_version
from install_and_test_tool_shed_repositories.base.util import get_repository_current_revision
from install_and_test_tool_shed_repositories.base.util import RepositoryMetadataApplication
from galaxy.model.orm import and_
from galaxy.model.orm import not_
from galaxy.model.orm import select
from galaxy.util import listify
from galaxy.web import url_for
from tool_shed.repository_types.util import TOOL_DEPENDENCY_DEFINITION

log = logging.getLogger()
log.setLevel( 10 )
log.addHandler( logging.StreamHandler( sys.stdout ) )

assert sys.version_info[ :2 ] >= ( 2, 6 )

def main():
    '''Script that validates all repositories of type tool_dependency_definition.'''
    parser = OptionParser()
    parser.add_option( "-i", "--info_only", action="store_true", dest="info_only", help="info about the requested action", default=False )
    parser.add_option( "-s", "--section", action="store", dest="section", default='server:main',
                       help=".ini file section from which to extract the host and port" )
    parser.add_option( "-v", "--verbose", action="count", dest="verbosity", default=1, help="Control the amount of detail in the log output." )
    parser.add_option( "--verbosity", action="store", dest="verbosity", metavar='VERBOSITY', type="int",
                       help="Control the amount of detail in the log output, --verbosity=1 is the same as -v" )
    ( options, args ) = parser.parse_args()
    try:
        ini_file = args[ 0 ]
    except IndexError:
        print "Usage: python %s <tool shed .ini file> [options]" % sys.argv[ 0 ]
        exit( 127 )
    config_parser = ConfigParser.ConfigParser( { 'here':os.getcwd() } )
    config_parser.read( ini_file )
    config_dict = {}
    for key, value in config_parser.items( "app:main" ):
        config_dict[ key ] = value
    config = tool_shed_config.Configuration( **config_dict )
    config_section = options.section

    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "#############################################################################"
    print "# %s - Validating repositories of type %s" % ( now, TOOL_DEPENDENCY_DEFINITION )
    print "# This tool shed is configured to listen on %s:%s" % ( config_parser.get( config_section, 'host' ),
                                                                  config_parser.get( config_section, 'port' ) )
    
    app = RepositoryMetadataApplication( config )
    if options.info_only:
        print "# Displaying info only ( --info_only )"
    if options.verbosity:
        print "# Displaying extra information ( --verbosity = %d )" % options.verbosity
    validate_repositories( app, info_only=options.info_only, verbosity=options.verbosity )

def validate_repositories( app, info_only=False, verbosity=1 ):
    """
    Inspect records in the repository_metadata table that are associated with repositories of type TOOL_DEPENDENCY_DEFINITION
    to ensure they are valid and set the repository_metadata.do_not_test column value to True if the metadata is invalid.
    Each repository's metadata should look something like:
    "{"tool_dependencies": 
        {"libpng/1.2.5": {"name": "libpng", 
                          "readme": "README content", 
                          "type": "package", 
                          "version": "1.2.5"}}}"
    or:
    "{"repository_dependencies": 
        {"description": null, 
         "repository_dependencies": 
             [["http://localhost:9009", "package_libpng_1_2", "iuc", "5788512d4c0a", "True", "False"]]}, 
         "tool_dependencies": 
             {"libgd/2.1.0": 
                 {"name": "libgd", "readme": "text"}, 
              "libpng/1.2.5": 
                 {"name": "libpng", "type": "package", "version": "1.2.5"}}}"
    """
    invalid_metadata = 0
    records_checked = 0
    skip_metadata_ids = []
    start = time.time()
    valid_metadata = 0
    # Restrict testing to repositories of type TOOL_DEPENDENCY_DEFINITION
    tool_dependency_defintion_repository_ids = []
    for repository in app.sa_session.query( app.model.Repository ) \
                                    .filter( and_( app.model.Repository.table.c.deleted == False,
                                                   app.model.Repository.table.c.type == TOOL_DEPENDENCY_DEFINITION ) ):
        tool_dependency_defintion_repository_ids.append( repository.id )
    # Do not check metadata records that have an entry in the skip_tool_tests table, since they won't be tested anyway.
    skip_metadata_ids = select( [ app.model.SkipToolTest.table.c.repository_metadata_id ] )
    # Get the list of metadata records to check, restricting it to records that have not been flagged do_not_test.
    for repository_metadata in \
        app.sa_session.query( app.model.RepositoryMetadata ) \
                      .filter( and_( app.model.RepositoryMetadata.table.c.downloadable == True,
                                     app.model.RepositoryMetadata.table.c.do_not_test == False,
                                     app.model.RepositoryMetadata.table.c.repository_id.in_( tool_dependency_defintion_repository_ids ),
                                     not_( app.model.RepositoryMetadata.table.c.id.in_( skip_metadata_ids ) ) ) ):
        records_checked += 1
        # Check the next repository revision.
        changeset_revision = str( repository_metadata.changeset_revision )
        name = repository.name
        owner = repository.user.username
        metadata = repository_metadata.metadata
        repository = repository_metadata.repository
        if verbosity >= 1:
            print '# -------------------------------------------------------------------------------------------'
            print '# Checking revision %s of %s owned by %s.' % ( changeset_revision, name, owner )
        if metadata:
            # Valid metadata will undoubtedly have a tool_dependencies entry or  repository_dependencies entry.
            repository_dependencies = metadata.get( 'repository_dependencies', None )
            tool_dependencies = metadata.get( 'tool_dependencies', None )
            if repository_dependencies or tool_dependencies:
                print 'Revision %s of %s owned by %s has valid metadata.' % ( changeset_revision, name, owner )
                valid_metadata += 1
            else:
                if verbosity >= 1:
                    print 'Revision %s of %s owned by %s has invalid metadata.' % ( changeset_revision, name, owner )
                invalid_metadata += 1
            if not info_only:
                # Create the tool_test_results_dict dictionary, using the dictionary from the previous test run if available.
                if repository_metadata.tool_test_results is not None:
                    # We'll listify the column value in case it uses the old approach of storing the results of only a single test run.
                    tool_test_results_dicts = listify( repository_metadata.tool_test_results )
                else:
                    tool_test_results_dicts = []
                if tool_test_results_dicts:
                    # Inspect the tool_test_results_dict for the last test run in case it contains only a test_environment
                    # entry.  This will occur with multiple runs of this script without running the associated
                    # install_and_test_tool_sed_repositories.sh script which will further populate the tool_test_results_dict.
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
                    # Create a new dictionary for the most recent test run.
                    tool_test_results_dict = {}
                # Initialize the tool_test_results_dict dictionary with the information about the current test environment.
                test_environment_dict = tool_test_results_dict.get( 'test_environment', {} )
                test_environment_dict[ 'tool_shed_database_version' ] = get_database_version( app )
                test_environment_dict[ 'tool_shed_mercurial_version' ] = __version__.version
                test_environment_dict[ 'tool_shed_revision' ] = get_repository_current_revision( os.getcwd() )
                tool_test_results_dict[ 'test_environment' ] = test_environment_dict
                # Store only the configured number of test runs.
                num_tool_test_results_saved = int( app.config.num_tool_test_results_saved )
                if len( tool_test_results_dicts ) >= num_tool_test_results_saved:
                    test_results_index = num_tool_test_results_saved - 1
                    new_tool_test_results_dicts = tool_test_results_dicts[ :test_results_index ]
                else:
                    new_tool_test_results_dicts = [ d for d in tool_test_results_dicts ]
                # Insert the new element into the first position in the list.
                new_tool_test_results_dicts.insert( 0, tool_test_results_dict )
                repository_metadata.tool_test_results = new_tool_test_results_dicts
                app.sa_session.add( repository_metadata )
                app.sa_session.flush()
    stop = time.time()
    print '# -------------------------------------------------------------------------------------------'
    print '# Checked %d repository revisions.' % records_checked
    print '# %d revisions found with valid tool dependency definition metadata.' % valid_metadata
    print '# %d revisions found with invalid tool dependency definition metadata.' % invalid_metadata
    if info_only:
        print '# Database not updated with any information from this run.'
    print "# Elapsed time: ", stop - start
    print "#############################################################################"

if __name__ == "__main__": main()
