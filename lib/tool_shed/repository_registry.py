import os
import logging

import tool_shed.repository_types.util as rt_util

from galaxy.model.orm import and_
from galaxy.model.orm import or_
from galaxy.webapps.tool_shed import model

from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import shed_util_common as suc

log = logging.getLogger( __name__ )


class Registry( object ):

    def __init__( self, app ):
        log.debug( "Loading the repository registry..." )
        self.app = app
        self.certified_level_one_clause_list = self.get_certified_level_one_clause_list()
        # The following lists contain tuples like ( repository.name, repository.user.username, changeset_revision )
        # where the changeset_revision entry is always the latest installable changeset_revision..
        self.certified_level_one_repository_and_suite_tuples = []
        self.certified_level_one_suite_tuples = []
        # These category dictionaries contain entries where the key is the category and the value is the integer count
        # of viewable repositories within that category.
        self.certified_level_one_viewable_repositories_and_suites_by_category = {}
        self.certified_level_one_viewable_suites_by_category = {}
        self.certified_level_two_repository_and_suite_tuples = []
        self.certified_level_two_suite_tuples = []
        self.certified_level_two_viewable_repositories_and_suites_by_category = {}
        self.certified_level_two_viewable_suites_by_category = {}
        self.repository_and_suite_tuples = []
        self.suite_tuples = []
        self.viewable_repositories_and_suites_by_category = {}
        self.viewable_suites_by_category = {}
        self.viewable_valid_repositories_and_suites_by_category = {}
        self.viewable_valid_suites_by_category = {}
        self.load_viewable_repositories_and_suites_by_category()
        self.load_repository_and_suite_tuples()

    def add_category_entry( self, category ):
        category_name = str( category.name )
        if category_name not in self.viewable_repositories_and_suites_by_category:
            self.viewable_repositories_and_suites_by_category[ category_name ] = 0
        if category_name not in self.viewable_suites_by_category:
            self.viewable_suites_by_category[ category_name ] = 0
        if category_name not in self.viewable_valid_repositories_and_suites_by_category:
            self.viewable_valid_repositories_and_suites_by_category[ category_name ] = 0
        if category_name not in self.viewable_valid_suites_by_category:
            self.viewable_valid_suites_by_category[ category_name ] = 0
        if category_name not in self.certified_level_one_viewable_repositories_and_suites_by_category:
            self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] = 0
        if category_name not in self.certified_level_one_viewable_suites_by_category:
            self.certified_level_one_viewable_suites_by_category[ category_name ] = 0

    def add_entry( self, repository ):
        try:
            if repository:
                is_valid = self.is_valid( repository )
                certified_level_one_tuple = self.get_certified_level_one_tuple( repository )
                latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
                for rca in repository.categories:
                    category = rca.category
                    category_name = str( category.name )
                    if category_name in self.viewable_repositories_and_suites_by_category:
                        self.viewable_repositories_and_suites_by_category[ category_name ] += 1
                    else:
                        self.viewable_repositories_and_suites_by_category[ category_name ] = 1
                    if is_valid:
                        if category_name in self.viewable_valid_repositories_and_suites_by_category:
                            self.viewable_valid_repositories_and_suites_by_category[ category_name ] += 1
                        else:
                            self.viewable_valid_repositories_and_suites_by_category[ category_name ] = 1
                    if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                        if category_name in self.viewable_suites_by_category:
                            self.viewable_suites_by_category[ category_name ] += 1
                        else:
                            self.viewable_suites_by_category[ category_name ] = 1
                        if is_valid:
                            if category_name in self.viewable_valid_suites_by_category:
                                self.viewable_valid_suites_by_category[ category_name ] += 1
                            else:
                                self.viewable_valid_suites_by_category[ category_name ] = 1
                    if is_level_one_certified:
                        if category_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] += 1
                        else:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] = 1
                        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                            if category_name in self.certified_level_one_viewable_suites_by_category:
                                self.certified_level_one_viewable_suites_by_category[ category_name ] += 1
                            else:
                                self.certified_level_one_viewable_suites_by_category[ category_name ] = 1
                self.load_repository_and_suite_tuple( repository )
                if is_level_one_certified:
                    self.load_certified_level_one_repository_and_suite_tuple( repository )
        except Exception, e:
            # The viewable repository numbers and the categorized (filtered) lists of repository tuples
            # may be slightly skewed, but that is no reason to result in a potential server error.  All
            # will be corrected at next server start.
            log.exception( "Handled error adding entry to repository registry: %s." % str( e ) )

    def edit_category_entry( self, old_name, new_name ):
        if old_name in self.viewable_repositories_and_suites_by_category:
            val = self.viewable_repositories_and_suites_by_category[ old_name ]
            del self.viewable_repositories_and_suites_by_category[ old_name ]
            self.viewable_repositories_and_suites_by_category[ new_name ] = val
        else:
            self.viewable_repositories_and_suites_by_category[ new_name ] = 0
        if old_name in self.viewable_valid_repositories_and_suites_by_category:
            val = self.viewable_valid_repositories_and_suites_by_category[ old_name ]
            del self.viewable_valid_repositories_and_suites_by_category[ old_name ]
            self.viewable_valid_repositories_and_suites_by_category[ new_name ] = val
        else:
            self.viewable_valid_repositories_and_suites_by_category[ new_name ] = 0
        if old_name in self.viewable_suites_by_category:
            val = self.viewable_suites_by_category[ old_name ]
            del self.viewable_suites_by_category[ old_name ]
            self.viewable_suites_by_category[ new_name ] = val
        else:
            self.viewable_suites_by_category[ new_name ] = 0
        if old_name in self.viewable_valid_suites_by_category:
            val = self.viewable_valid_suites_by_category[ old_name ]
            del self.viewable_valid_suites_by_category[ old_name ]
            self.viewable_valid_suites_by_category[ new_name ] = val
        else:
            self.viewable_valid_suites_by_category[ new_name ] = 0
        if old_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
            val = self.certified_level_one_viewable_repositories_and_suites_by_category[ old_name ]
            del self.certified_level_one_viewable_repositories_and_suites_by_category[ old_name ]
            self.certified_level_one_viewable_repositories_and_suites_by_category[ new_name ] = val
        else:
            self.certified_level_one_viewable_repositories_and_suites_by_category[ new_name ] = 0
        if old_name in self.certified_level_one_viewable_suites_by_category:
            val = self.certified_level_one_viewable_suites_by_category[ old_name ]
            del self.certified_level_one_viewable_suites_by_category[ old_name ]
            self.certified_level_one_viewable_suites_by_category[ new_name ] = val
        else:
            self.certified_level_one_viewable_suites_by_category[ new_name ] = 0

    def get_certified_level_one_clause_list( self ):
        certified_level_one_tuples = []
        clause_list = []
        for repository in self.sa_session.query( model.Repository ) \
                                         .filter( and_( model.Repository.table.c.deleted == False,
                                                        model.Repository.table.c.deprecated == False ) ):
            certified_level_one_tuple = self.get_certified_level_one_tuple( repository )
            latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
            if is_level_one_certified:
                certified_level_one_tuples.append( certified_level_one_tuple )
                clause_list.append( "%s=%d and %s='%s'" % ( model.RepositoryMetadata.table.c.repository_id,
                                                            repository.id,
                                                            model.RepositoryMetadata.table.c.changeset_revision,
                                                            latest_installable_changeset_revision ) )
        return clause_list

    def get_certified_level_one_tuple( self, repository ):
        """
        Return True if the latest installable changeset_revision of the received repository is level one certified.
        """
        if repository is None:
            return ( None, False )
        if repository.deleted or repository.deprecated:
            return ( None, False )
        repo = hg_util.get_repo_for_repository( self.app, repository=repository, repo_path=None, create=False )
        # Get the latest installable changeset revision since that is all that is currently configured for testing.
        latest_installable_changeset_revision = suc.get_latest_downloadable_changeset_revision( self.app, repository, repo )
        if latest_installable_changeset_revision not in [ None, hg_util.INITIAL_CHANGELOG_HASH ]:
            encoded_repository_id = self.app.security.encode_id( repository.id )
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app,
                                                                                     encoded_repository_id,
                                                                                     latest_installable_changeset_revision )
            if repository_metadata:
                # Filter out repository revisions that have not been tested.
                if repository_metadata.time_last_tested is not None and repository_metadata.tool_test_results is not None:
                    if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION, rt_util.TOOL_DEPENDENCY_DEFINITION ]:
                        # Look in the tool_test_results dictionary for installation errors.
                        try:
                            tool_test_results_dict = repository_metadata.tool_test_results[ 0 ]
                        except Exception, e:
                            message = 'Error attempting to retrieve install and test results for repository %s:\n' % str( repository.name )
                            message += '%s' % str( e )
                            log.exception( message )
                            return ( latest_installable_changeset_revision, False )
                        if 'installation_errors' in tool_test_results_dict:
                            return ( latest_installable_changeset_revision, False )
                        return ( latest_installable_changeset_revision, True )
                    else:
                        # We have a repository with type Unrestricted.
                        if repository_metadata.includes_tools:
                            if repository_metadata.tools_functionally_correct:
                                return ( latest_installable_changeset_revision, True )
                            return ( latest_installable_changeset_revision, False )
                        else:
                            # Look in the tool_test_results dictionary for installation errors.
                            try:
                                tool_test_results_dict = repository_metadata.tool_test_results[ 0 ]
                            except Exception, e:
                                message = 'Error attempting to retrieve install and test results for repository %s:\n' % str( repository.name )
                                message += '%s' % str( e )
                                log.exception( message )
                                return ( latest_installable_changeset_revision, False )
                            if 'installation_errors' in tool_test_results_dict:
                                return ( latest_installable_changeset_revision, False )
                            return ( latest_installable_changeset_revision, True )
                else:
                    # No test results.
                    return ( latest_installable_changeset_revision, False )
            else:
                # No repository_metadata.
                return ( latest_installable_changeset_revision, False )
        else:
            # No installable changeset_revision.
            return ( None, False )

    def is_level_one_certified( self, repository_metadata ):
        if repository_metadata:
            repository = repository_metadata.repository
            if repository:
                if repository.deprecated or repository.deleted:
                    return False
                tuple = ( str( repository.name ), str( repository.user.username ), str( repository_metadata.changeset_revision ) )
                if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION ]:
                    return tuple in self.certified_level_one_suite_tuples
                else:
                    return tuple in self.certified_level_one_repository_and_suite_tuples
        return False

    def is_valid( self, repository ):
        if repository and not repository.deleted and not repository.deprecated and repository.downloadable_revisions:
            return True
        return False

    def load_certified_level_one_repository_and_suite_tuple( self, repository ):
        # The received repository has been determined to be level one certified.
        name = str( repository.name )
        owner = str( repository.user.username )
        tip_changeset_hash = repository.tip( self.app )
        if tip_changeset_hash != hg_util.INITIAL_CHANGELOG_HASH:
            certified_level_one_tuple = ( name, owner, tip_changeset_hash )
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if certified_level_one_tuple not in self.certified_level_one_suite_tuples:
                    self.certified_level_one_suite_tuples.append( certified_level_one_tuple )
            else:
                if certified_level_one_tuple not in self.certified_level_one_repository_and_suite_tuples:
                    self.certified_level_one_repository_and_suite_tuples.append( certified_level_one_tuple )

    def load_repository_and_suite_tuple( self, repository ):
        name = str( repository.name )
        owner = str( repository.user.username )
        for repository_metadata in repository.metadata_revisions:
            changeset_revision = str( repository_metadata.changeset_revision )
            tuple = ( name, owner, changeset_revision )
            if tuple not in self.repository_and_suite_tuples:
                self.repository_and_suite_tuples.append( tuple )
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if tuple not in self.suite_tuples:
                    self.suite_tuples.append( tuple )

    def load_repository_and_suite_tuples( self ):
        # Load self.certified_level_one_repository_and_suite_tuples and self.certified_level_one_suite_tuples.
        for repository in self.sa_session.query( model.Repository ) \
                                         .join( model.RepositoryMetadata.table ) \
                                         .filter( or_( *self.certified_level_one_clause_list ) ) \
                                         .join( model.User.table ):
            self.load_certified_level_one_repository_and_suite_tuple( repository )
        # Load self.repository_and_suite_tuples and self.suite_tuples
        for repository in self.sa_session.query( model.Repository ) \
                                         .filter( and_( model.Repository.table.c.deleted == False,
                                                        model.Repository.table.c.deprecated == False ) ) \
                                         .join( model.User.table ):
           self.load_repository_and_suite_tuple( repository )

    def load_viewable_repositories_and_suites_by_category( self ):
        # Clear all dictionaries just in case they were previously loaded.
        self.certified_level_one_viewable_repositories_and_suites_by_category = {}
        self.certified_level_one_viewable_suites_by_category = {}
        self.certified_level_two_viewable_repositories_and_suites_by_category = {}
        self.certified_level_two_viewable_suites_by_category = {}
        self.viewable_repositories_and_suites_by_category = {}
        self.viewable_suites_by_category = {}
        self.viewable_valid_repositories_and_suites_by_category = {}
        self.viewable_valid_suites_by_category = {}
        for category in self.sa_session.query( model.Category ):
            category_name = str( category.name )
            if category not in self.certified_level_one_viewable_repositories_and_suites_by_category:
                self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] = 0
            if category not in self.certified_level_one_viewable_suites_by_category:
                self.certified_level_one_viewable_suites_by_category[ category_name ] = 0
            if category not in self.viewable_repositories_and_suites_by_category:
                self.viewable_repositories_and_suites_by_category[ category_name ] = 0
            if category not in self.viewable_suites_by_category:
                self.viewable_suites_by_category[ category_name ] = 0
            if category not in self.viewable_valid_repositories_and_suites_by_category:
                self.viewable_valid_repositories_and_suites_by_category[ category_name ] = 0
            if category not in self.viewable_valid_suites_by_category:
                self.viewable_valid_suites_by_category[ category_name ] = 0
            for rca in category.repositories:
                repository = rca.repository
                if not repository.deleted and not repository.deprecated:
                    is_valid = self.is_valid( repository )
                    encoded_repository_id = self.app.security.encode_id( repository.id )
                    tip_changeset_hash = repository.tip( self.app )
                    repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app,
                                                                                             encoded_repository_id,
                                                                                             tip_changeset_hash )
                    self.viewable_repositories_and_suites_by_category[ category_name ] += 1
                    if is_valid:
                        self.viewable_valid_repositories_and_suites_by_category[ category_name ] += 1
                    if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION ]:
                        self.viewable_suites_by_category[ category_name ] += 1
                        if is_valid:
                            self.viewable_valid_suites_by_category[ category_name ] += 1
                    if self.is_level_one_certified( repository_metadata ):
                        self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] += 1
                        if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION ]:
                            self.certified_level_one_viewable_suites_by_category[ category_name ] += 1

    def remove_category_entry( self, category ):
        catgeory_name = str( category.name )
        if catgeory_name in self.viewable_repositories_and_suites_by_category:
            del self.viewable_repositories_and_suites_by_category[ catgeory_name ]
        if catgeory_name in self.viewable_valid_repositories_and_suites_by_category:
            del self.viewable_valid_repositories_and_suites_by_category[ catgeory_name ]
        if catgeory_name in self.viewable_suites_by_category:
            del self.viewable_suites_by_category[ catgeory_name ]
        if catgeory_name in self.viewable_valid_suites_by_category:
            del self.viewable_valid_suites_by_category[ catgeory_name ]
        if catgeory_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
            del self.certified_level_one_viewable_repositories_and_suites_by_category[ catgeory_name ]
        if catgeory_name in self.certified_level_one_viewable_suites_by_category:
            del self.certified_level_one_viewable_suites_by_category[ catgeory_name ]

    def remove_entry( self, repository ):
        try:
            if repository:
                is_valid = self.is_valid( repository )
                certified_level_one_tuple = self.get_certified_level_one_tuple( repository )
                latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
                for rca in repository.categories:
                    category = rca.category
                    category_name = str( category.name )
                    if category_name in self.viewable_repositories_and_suites_by_category:
                        if self.viewable_repositories_and_suites_by_category[ category_name ] > 0:
                            self.viewable_repositories_and_suites_by_category[ category_name ] -= 1
                    else:
                        self.viewable_repositories_and_suites_by_category[ category_name ] = 0
                    if is_valid:
                        if category_name in self.viewable_valid_repositories_and_suites_by_category:
                            if self.viewable_valid_repositories_and_suites_by_category[ category_name ] > 0:
                                self.viewable_valid_repositories_and_suites_by_category[ category_name ] -= 1
                        else:
                            self.viewable_valid_repositories_and_suites_by_category[ category_name ] = 0
                    if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                        if category_name in self.viewable_suites_by_category:
                            if self.viewable_suites_by_category[ category_name ] > 0:
                                self.viewable_suites_by_category[ category_name ] -= 1
                        else:
                            self.viewable_suites_by_category[ category_name ] = 0
                        if is_valid:
                            if category_name in self.viewable_valid_suites_by_category:
                                if self.viewable_valid_suites_by_category[ category_name ] > 0:
                                    self.viewable_valid_suites_by_category[ category_name ] -= 1
                            else:
                                self.viewable_valid_suites_by_category[ category_name ] = 0
                    if is_level_one_certified:
                        if category_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
                            if self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] > 0:
                                self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] -= 1
                        else:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[ category_name ] = 0
                        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                            if category_name in self.certified_level_one_viewable_suites_by_category:
                                if self.certified_level_one_viewable_suites_by_category[ category_name ] > 0:
                                    self.certified_level_one_viewable_suites_by_category[ category_name ] -= 1
                            else:
                                self.certified_level_one_viewable_suites_by_category[ category_name ] = 0
                self.unload_repository_and_suite_tuple( repository )
                if is_level_one_certified:
                    self.unload_certified_level_one_repository_and_suite_tuple( repository )
        except Exception, e:
            # The viewable repository numbers and the categorized (filtered) lists of repository tuples
            # may be slightly skewed, but that is no reason to result in a potential server error.  All
            # will be corrected at next server start.
            log.exception( "Handled error removing entry from repository registry: %s." % str( e ) )

    @property
    def sa_session( self ):
        return self.app.model.context.current

    def unload_certified_level_one_repository_and_suite_tuple( self, repository ):
        # The received repository has been determined to be level one certified.
        name = str( repository.name )
        owner = str( repository.user.username )
        tip_changeset_hash = repository.tip( self.app )
        if tip_changeset_hash != hg_util.INITIAL_CHANGELOG_HASH:
            certified_level_one_tuple = ( name, owner, tip_changeset_hash )
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if certified_level_one_tuple in self.certified_level_one_suite_tuples:
                    self.certified_level_one_suite_tuples.remove( certified_level_one_tuple )
            else:
                if certified_level_one_tuple in self.certified_level_one_repository_and_suite_tuples:
                    self.certified_level_one_repository_and_suite_tuples.remove( certified_level_one_tuple )

    def unload_repository_and_suite_tuple( self, repository ):
        name = str( repository.name )
        owner = str( repository.user.username )
        for repository_metadata in repository.metadata_revisions:
            changeset_revision = str( repository_metadata.changeset_revision )
            tuple = ( name, owner, changeset_revision )
            if tuple in self.repository_and_suite_tuples:
                self.repository_and_suite_tuples.remove( tuple )
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if tuple in self.suite_tuples:
                    self.suite_tuples.remove( tuple )
