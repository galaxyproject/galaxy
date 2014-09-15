import logging
import os
import tempfile

from galaxy import util
from galaxy.util import inflector
from galaxy.web.form_builder import SelectField

from tool_shed.metadata import metadata_generator
from tool_shed.repository_types.metadata import TipOnly
from tool_shed.repository_types import util as rt_util

from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_util

log = logging.getLogger( __name__ )


class RepositoryMetadataManager( metadata_generator.MetadataGenerator ):

    def __init__( self, app, user, repository=None, changeset_revision=None, repository_clone_url=None,
                  shed_config_dict=None, relative_install_dir=None, repository_files_dir=None,
                  resetting_all_metadata_on_repository=False, updating_installed_repository=False,
                  persist=False, metadata_dict=None ):
        super( RepositoryMetadataManager, self ).__init__( app, repository, changeset_revision,
                                                           repository_clone_url, shed_config_dict,
                                                           relative_install_dir, repository_files_dir,
                                                           resetting_all_metadata_on_repository,
                                                           updating_installed_repository, persist,
                                                           metadata_dict=metadata_dict, user=user )
        self.app = app
        self.user = user
        # Repository metadata comparisons for changeset revisions.
        self.EQUAL = 'equal'
        self.NO_METADATA = 'no metadata'
        self.NOT_EQUAL_AND_NOT_SUBSET = 'not equal and not subset'
        self.SUBSET = 'subset'
        self.SUBSET_VALUES = [ self.EQUAL, self.SUBSET ]

    def add_tool_versions( self, id, repository_metadata, changeset_revisions ):
        # Build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in repository_metadata.
        metadata = repository_metadata.metadata
        tool_versions_dict = {}
        for tool_dict in metadata.get( 'tools', [] ):
            # We have at least 2 changeset revisions to compare tool guids and tool ids.
            parent_id = self.get_parent_id( id,
                                            tool_dict[ 'id' ],
                                            tool_dict[ 'version' ],
                                            tool_dict[ 'guid' ],
                                            changeset_revisions )
            tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
        if tool_versions_dict:
            repository_metadata.tool_versions = tool_versions_dict
            self.sa_session.add( repository_metadata )
            self.sa_session.flush()

    def build_repository_ids_select_field( self, name='repository_ids', multiple=True, display='checkboxes',
                                           my_writable=False ):
        """Generate the current list of repositories for resetting metadata."""
        repositories_select_field = SelectField( name=name, multiple=multiple, display=display )
        query = self.get_query_for_setting_metadata_on_repositories( my_writable=my_writable, order=True )
        for repository in query:
            owner = str( repository.user.username )
            option_label = '%s (%s)' % ( str( repository.name ), owner )
            option_value = '%s' % self.app.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
        return repositories_select_field

    def clean_repository_metadata( self, changeset_revisions ):
        # Delete all repository_metadata records associated with the repository that have
        # a changeset_revision that is not in changeset_revisions.  We sometimes see multiple
        # records with the same changeset revision value - no idea how this happens. We'll
        # assume we can delete the older records, so we'll order by update_time descending and
        # delete records that have the same changeset_revision we come across later.
        changeset_revisions_checked = []
        for repository_metadata in \
            self.sa_session.query( self.app.model.RepositoryMetadata ) \
                           .filter( self.app.model.RepositoryMetadata.table.c.repository_id == self.repository.id ) \
                           .order_by( self.app.model.RepositoryMetadata.table.c.changeset_revision,
                                      self.app.model.RepositoryMetadata.table.c.update_time.desc() ):
            changeset_revision = repository_metadata.changeset_revision
            if changeset_revision in changeset_revisions_checked or changeset_revision not in changeset_revisions:
                self.sa_session.delete( repository_metadata )
                self.sa_session.flush()

    def compare_changeset_revisions( self, ancestor_changeset_revision, ancestor_metadata_dict ):
        """
        Compare the contents of two changeset revisions to determine if a new repository
        metadata revision should be created.
        """
        # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.
        # This changeset_revision is an ancestor of self.changeset_revision which is associated
        # with self.metadata_dict.  A new repository_metadata record will be created only
        # when this method returns the constant value self.NOT_EQUAL_AND_NOT_SUBSET.
        ancestor_datatypes = ancestor_metadata_dict.get( 'datatypes', [] )
        ancestor_tools = ancestor_metadata_dict.get( 'tools', [] )
        ancestor_guids = [ tool_dict[ 'guid' ] for tool_dict in ancestor_tools ]
        ancestor_guids.sort()
        ancestor_readme_files = ancestor_metadata_dict.get( 'readme_files', [] )
        ancestor_repository_dependencies_dict = ancestor_metadata_dict.get( 'repository_dependencies', {} )
        ancestor_repository_dependencies = ancestor_repository_dependencies_dict.get( 'repository_dependencies', [] )
        ancestor_tool_dependencies = ancestor_metadata_dict.get( 'tool_dependencies', {} )
        ancestor_workflows = ancestor_metadata_dict.get( 'workflows', [] )
        ancestor_data_manager = ancestor_metadata_dict.get( 'data_manager', {} )
        current_datatypes = self.metadata_dict.get( 'datatypes', [] )
        current_tools = self.metadata_dict.get( 'tools', [] )
        current_guids = [ tool_dict[ 'guid' ] for tool_dict in current_tools ]
        current_guids.sort()
        current_readme_files = self.metadata_dict.get( 'readme_files', [] )
        current_repository_dependencies_dict = self.metadata_dict.get( 'repository_dependencies', {} )
        current_repository_dependencies = current_repository_dependencies_dict.get( 'repository_dependencies', [] )
        current_tool_dependencies = self.metadata_dict.get( 'tool_dependencies', {} )
        current_workflows = self.metadata_dict.get( 'workflows', [] )
        current_data_manager = self.metadata_dict.get( 'data_manager', {} )
        # Handle case where no metadata exists for either changeset.
        no_datatypes = not ancestor_datatypes and not current_datatypes
        no_readme_files = not ancestor_readme_files and not current_readme_files
        no_repository_dependencies = not ancestor_repository_dependencies and not current_repository_dependencies
        no_tool_dependencies = not ancestor_tool_dependencies and not current_tool_dependencies
        no_tools = not ancestor_guids and not current_guids
        no_workflows = not ancestor_workflows and not current_workflows
        no_data_manager = not ancestor_data_manager and not current_data_manager
        if no_datatypes and \
            no_readme_files and \
            no_repository_dependencies and \
            no_tool_dependencies and \
            no_tools and no_workflows and \
            no_data_manager:
            return self.NO_METADATA
        # Uncomment the following if we decide that README files should affect how installable
        # repository revisions are defined.  See the NOTE in self.compare_readme_files().
        # readme_file_comparision = self.compare_readme_files( ancestor_readme_files, current_readme_files )
        repository_dependency_comparison = self.compare_repository_dependencies( ancestor_repository_dependencies,
                                                                                 current_repository_dependencies )
        tool_dependency_comparison = self.compare_tool_dependencies( ancestor_tool_dependencies,
                                                                     current_tool_dependencies )
        workflow_comparison = self.compare_workflows( ancestor_workflows, current_workflows )
        datatype_comparison = self.compare_datatypes( ancestor_datatypes, current_datatypes )
        data_manager_comparison = self.compare_data_manager( ancestor_data_manager, current_data_manager )
        # Handle case where all metadata is the same.
        if ancestor_guids == current_guids and \
            repository_dependency_comparison == self.EQUAL and \
            tool_dependency_comparison == self.EQUAL and \
            workflow_comparison == self.EQUAL and \
            datatype_comparison == self.EQUAL and \
            data_manager_comparison == self.EQUAL:
            return self.EQUAL
        # Handle case where ancestor metadata is a subset of current metadata.
        # readme_file_is_subset = readme_file_comparision in [ self.EQUAL, self.SUBSET ]
        repository_dependency_is_subset = repository_dependency_comparison in self.SUBSET_VALUES
        tool_dependency_is_subset = tool_dependency_comparison in self.SUBSET_VALUES
        workflow_dependency_is_subset = workflow_comparison in self.SUBSET_VALUES
        datatype_is_subset = datatype_comparison in self.SUBSET_VALUES
        datamanager_is_subset = data_manager_comparison in self.SUBSET_VALUES
        if repository_dependency_is_subset and \
            tool_dependency_is_subset and \
            workflow_dependency_is_subset and \
            datatype_is_subset and \
            datamanager_is_subset:
            is_subset = True
            for guid in ancestor_guids:
                if guid not in current_guids:
                    is_subset = False
                    break
            if is_subset:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_data_manager( self, ancestor_metadata, current_metadata ):
        """Determine if ancestor_metadata is the same as or a subset of current_metadata for data_managers."""
        def __data_manager_dict_to_tuple_list( metadata_dict ):
            # we do not check tool_guid or tool conf file name
            return set( sorted( [ ( name,
                                    tuple( sorted( value.get( 'data_tables', [] ) ) ),
                                    value.get( 'guid'  ),
                                    value.get( 'version' ),
                                    value.get( 'name' ),
                                    value.get( 'id' )  ) for name, value in metadata_dict.iteritems() ] ) )
        # only compare valid entries, any invalid entries are ignored
        ancestor_metadata = __data_manager_dict_to_tuple_list( ancestor_metadata.get( 'data_managers', {} ) )
        current_metadata = __data_manager_dict_to_tuple_list( current_metadata.get( 'data_managers', {} ) )
        # use set comparisons
        if ancestor_metadata.issubset( current_metadata ):
            if ancestor_metadata == current_metadata:
                return self.EQUAL
            return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_datatypes( self, ancestor_datatypes, current_datatypes ):
        """Determine if ancestor_datatypes is the same as or a subset of current_datatypes."""
        # Each datatype dict looks something like: 
        # {"dtype": "galaxy.datatypes.images:Image", "extension": "pdf", "mimetype": "application/pdf"}
        if len( ancestor_datatypes ) <= len( current_datatypes ):
            for ancestor_datatype in ancestor_datatypes:
                # Currently the only way to differentiate datatypes is by name.
                ancestor_datatype_dtype = ancestor_datatype[ 'dtype' ]
                ancestor_datatype_extension = ancestor_datatype[ 'extension' ]
                ancestor_datatype_mimetype = ancestor_datatype.get( 'mimetype', None )
                found_in_current = False
                for current_datatype in current_datatypes:
                    if current_datatype[ 'dtype' ] == ancestor_datatype_dtype and \
                        current_datatype[ 'extension' ] == ancestor_datatype_extension and \
                        current_datatype.get( 'mimetype', None ) == ancestor_datatype_mimetype:
                        found_in_current = True
                        break
                if not found_in_current:
                    return self.NOT_EQUAL_AND_NOT_SUBSET
            if len( ancestor_datatypes ) == len( current_datatypes ):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_readme_files( self, ancestor_readme_files, current_readme_files ):
        """Determine if ancestor_readme_files is equal to or a subset of current_readme_files."""
        # NOTE: Although repository README files are considered a Galaxy utility similar to tools,
        # repository dependency definition files, etc., we don't define installable repository revisions
        # based on changes to README files.  To understand why, consider the following scenario:
        # 1. Upload the filtering tool to a new repository - this will result in installable revision 0.
        # 2. Upload a README file to the repository - this will move the installable revision from revision
        #    0 to revision 1.
        # 3. Delete the README file from the repository - this will move the installable revision from
        #    revision 1 to revision 2.
        # The above scenario is the current behavior, and that is why this method is not currently called.
        # This method exists only in case we decide to change this current behavior.
        # The lists of readme files looks something like: ["database/community_files/000/repo_2/readme.txt"]
        if len( ancestor_readme_files ) <= len( current_readme_files ):
            for ancestor_readme_file in ancestor_readme_files:
                if ancestor_readme_file not in current_readme_files:
                    return self.NOT_EQUAL_AND_NOT_SUBSET
            if len( ancestor_readme_files ) == len( current_readme_files ):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_repository_dependencies( self, ancestor_repository_dependencies, current_repository_dependencies ):
        """
        Determine if ancestor_repository_dependencies is the same as or a subset of
        current_repository_dependencies.
        """
        # The list of repository_dependencies looks something like:
        # [["http://localhost:9009", "emboss_datatypes", "test", "ab03a2a5f407", "False", "False"]].
        # Create a string from each tuple in the list for easier comparison.
        if len( ancestor_repository_dependencies ) <= len( current_repository_dependencies ):
            for ancestor_tup in ancestor_repository_dependencies:
                a_tool_shed, \
                a_repo_name, \
                a_repo_owner, \
                a_changeset_revision, \
                a_prior_installation_required, \
                a_only_if_compiling_contained_td = \
                    ancestor_tup
                cleaned_a_tool_shed = common_util.remove_protocol_from_tool_shed_url( a_tool_shed )
                found_in_current = False
                for current_tup in current_repository_dependencies:
                    c_tool_shed, \
                    c_repo_name, \
                    c_repo_owner, \
                    c_changeset_revision, \
                    c_prior_installation_required, \
                    c_only_if_compiling_contained_td = \
                        current_tup
                    cleaned_c_tool_shed = common_util.remove_protocol_from_tool_shed_url( c_tool_shed )
                    if cleaned_c_tool_shed == cleaned_a_tool_shed and \
                        c_repo_name == a_repo_name and \
                        c_repo_owner == a_repo_owner and \
                        c_changeset_revision == a_changeset_revision and \
                        util.string_as_bool( c_prior_installation_required ) == util.string_as_bool( a_prior_installation_required ) and \
                        util.string_as_bool( c_only_if_compiling_contained_td ) == util.string_as_bool( a_only_if_compiling_contained_td ):
                        found_in_current = True
                        break
                if not found_in_current:
                    # In some cases, the only difference between a dependency definition in the lists
                    # is the changeset_revision value.  We'll check to see if this is the case, and if
                    # the defined dependency is a repository that has metadata set only on its tip.
                    if not self.different_revision_defines_tip_only_repository_dependency( ancestor_tup,
                                                                                           current_repository_dependencies ):
                        return self.NOT_EQUAL_AND_NOT_SUBSET
                    return self.SUBSET
            if len( ancestor_repository_dependencies ) == len( current_repository_dependencies ):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_tool_dependencies( self, ancestor_tool_dependencies, current_tool_dependencies ):
        """
        Determine if ancestor_tool_dependencies is the same as or a subset of current_tool_dependencies.
        """
        # The tool_dependencies dictionary looks something like:
        # {'bwa/0.5.9': {'readme': 'some string', 'version': '0.5.9', 'type': 'package', 'name': 'bwa'}}
        if len( ancestor_tool_dependencies ) <= len( current_tool_dependencies ):
            for ancestor_td_key, ancestor_requirements_dict in ancestor_tool_dependencies.items():
                if ancestor_td_key in current_tool_dependencies:
                    # The only values that could have changed between the 2 dictionaries are the
                    # "readme" or "type" values.  Changing the readme value makes no difference.
                    # Changing the type will change the installation process, but for now we'll
                    # assume it was a typo, so new metadata shouldn't be generated.
                    continue
                else:
                    return self.NOT_EQUAL_AND_NOT_SUBSET
            # At this point we know that ancestor_tool_dependencies is at least a subset of current_tool_dependencies.
            if len( ancestor_tool_dependencies ) == len( current_tool_dependencies ):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_workflows( self, ancestor_workflows, current_workflows ):
        """
        Determine if ancestor_workflows is the same as current_workflows or if ancestor_workflows
        is a subset of current_workflows.
        """
        if len( ancestor_workflows ) <= len( current_workflows ):
            for ancestor_workflow_tup in ancestor_workflows:
                # ancestor_workflows is a list of tuples where each contained tuple is
                # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                ancestor_workflow_dict = ancestor_workflow_tup[1]
                # Currently the only way to differentiate workflows is by name.
                ancestor_workflow_name = ancestor_workflow_dict[ 'name' ]
                num_ancestor_workflow_steps = len( ancestor_workflow_dict[ 'steps' ] )
                found_in_current = False
                for current_workflow_tup in current_workflows:
                    current_workflow_dict = current_workflow_tup[1]
                    # Assume that if the name and number of steps are euqal, then the workflows
                    # are the same.  Of course, this may not be true...
                    if current_workflow_dict[ 'name' ] == ancestor_workflow_name and \
                        len( current_workflow_dict[ 'steps' ] ) == num_ancestor_workflow_steps:
                        found_in_current = True
                        break
                if not found_in_current:
                    return self.NOT_EQUAL_AND_NOT_SUBSET
            if len( ancestor_workflows ) == len( current_workflows ):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def create_or_update_repository_metadata( self, changeset_revision, metadata_dict ):
        """Create or update a repository_metadatqa record in the tool shed."""
        has_repository_dependencies = False
        has_repository_dependencies_only_if_compiling_contained_td = False
        includes_datatypes = False
        includes_tools = False
        includes_tool_dependencies = False
        includes_workflows = False
        if metadata_dict:
            repository_dependencies_dict = metadata_dict.get( 'repository_dependencies', {} )
            repository_dependencies = repository_dependencies_dict.get( 'repository_dependencies', [] )
            has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td = \
                suc.get_repository_dependency_types( repository_dependencies )
            if 'datatypes' in metadata_dict:
                includes_datatypes = True
            if 'tools' in metadata_dict:
                includes_tools = True
            if 'tool_dependencies' in metadata_dict:
                includes_tool_dependencies = True
            if 'workflows' in metadata_dict:
                includes_workflows = True
        if has_repository_dependencies or \
            has_repository_dependencies_only_if_compiling_contained_td or \
            includes_datatypes or \
            includes_tools or \
            includes_tool_dependencies or \
            includes_workflows:
            downloadable = True
        else:
            downloadable = False
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app,
                                                                                 self.app.security.encode_id( self.repository.id ),
                                                                                 changeset_revision )
        if repository_metadata:
            # A repository metadata record already exists with the received changeset_revision,
            # so we don't need to check the skip_tool_test table.
            check_skip_tool_test = False
            repository_metadata.metadata = metadata_dict
            repository_metadata.downloadable = downloadable
            repository_metadata.has_repository_dependencies = has_repository_dependencies
            repository_metadata.includes_datatypes = includes_datatypes
            repository_metadata.includes_tools = includes_tools
            repository_metadata.includes_tool_dependencies = includes_tool_dependencies
            repository_metadata.includes_workflows = includes_workflows
        else:
            # No repository_metadata record exists for the received changeset_revision, so we may
            # need to update the skip_tool_test table.
            check_skip_tool_test = True
            repository_metadata = \
                self.app.model.RepositoryMetadata( repository_id=self.repository.id,
                                                   changeset_revision=changeset_revision,
                                                   metadata=metadata_dict,
                                                   downloadable=downloadable,
                                                   has_repository_dependencies=has_repository_dependencies,
                                                   includes_datatypes=includes_datatypes,
                                                   includes_tools=includes_tools,
                                                   includes_tool_dependencies=includes_tool_dependencies,
                                                   includes_workflows=includes_workflows )
        # Always set the default values for the following columns.  When resetting all metadata
        # on a repository this will reset the values.
        repository_metadata.tools_functionally_correct = False
        repository_metadata.missing_test_components = False
        repository_metadata.test_install_error = False
        repository_metadata.do_not_test = False
        repository_metadata.time_last_tested = None
        repository_metadata.tool_test_results = None
        self.sa_session.add( repository_metadata )
        self.sa_session.flush()
        if check_skip_tool_test:
            # Since we created a new repository_metadata record, we may need to update the
            # skip_tool_test table to point to it.  Inspect each changeset revision in the
            # received repository's changelog (up to the received changeset revision) to see
            # if it is contained in the skip_tool_test table.  If it is, but is not associated
            # with a repository_metadata record, reset that skip_tool_test record to the newly
            # created repository_metadata record.
            repo = hg_util.get_repo_for_repository( self.app, repository=self.repository, repo_path=None, create=False )
            for changeset in repo.changelog:
                changeset_hash = str( repo.changectx( changeset ) )
                skip_tool_test = self.get_skip_tool_test_by_changeset_revision( changeset_hash )
                if skip_tool_test:
                    # We found a skip_tool_test record associated with the changeset_revision,
                    # so see if it has a valid repository_revision.
                    repository_revision = \
                        metadata_util.get_repository_metadata_by_id( self.app,
                                                                     self.app.security.encode_id( repository_metadata.id ) )
                    if repository_revision:
                        # The skip_tool_test record is associated with a valid repository_metadata
                        # record, so proceed.
                        continue
                    # We found a skip_tool_test record that is associated with an invalid
                    # repository_metadata record, so update it to point to the newly created
                    # repository_metadata record.  In some special cases there may be multiple
                    # skip_tool_test records that require updating, so we won't break here, we'll
                    # continue to inspect the rest of the changelog up to the received changeset_revision.
                    skip_tool_test.repository_metadata_id = repository_metadata.id
                    self.sa_session.add( skip_tool_test )
                    self.sa_session.flush()
                if changeset_hash == changeset_revision:
                    # Proceed no further than the received changeset_revision.
                    break
        return repository_metadata

    def different_revision_defines_tip_only_repository_dependency( self, rd_tup, repository_dependencies ):
        """
        Determine if the only difference between rd_tup and a dependency definition in the list of
        repository_dependencies is the changeset_revision value.
        """
        new_metadata_required = False
        rd_tool_shed, rd_name, rd_owner, rd_changeset_revision, rd_prior_installation_required, rd_only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( rd_tup )
        cleaned_rd_tool_shed = common_util.remove_protocol_from_tool_shed_url( rd_tool_shed )
        for repository_dependency in repository_dependencies:
            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                common_util.parse_repository_dependency_tuple( repository_dependency )
            cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
            if cleaned_rd_tool_shed == cleaned_tool_shed and rd_name == name and rd_owner == owner:
                # Determine if the repository represented by the dependency tuple is an instance of the repository type TipOnly.
                required_repository = suc.get_repository_by_name_and_owner( self.app, name, owner )
                repository_type_class = self.app.repository_types_registry.get_class_by_label( required_repository.type )
                return isinstance( repository_type_class, TipOnly )
        return False

    def get_parent_id( self, id, old_id, version, guid, changeset_revisions ):
        parent_id = None
        # Compare from most recent to oldest.
        changeset_revisions.reverse()
        for changeset_revision in changeset_revisions:
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app, id, changeset_revision )
            metadata = repository_metadata.metadata
            tools_dicts = metadata.get( 'tools', [] )
            for tool_dict in tools_dicts:
                if tool_dict[ 'guid' ] == guid:
                    # The tool has not changed between the compared changeset revisions.
                    continue
                if tool_dict[ 'id' ] == old_id and tool_dict[ 'version' ] != version:
                    # The tool version is different, so we've found the parent.
                    return tool_dict[ 'guid' ]
        if parent_id is None:
            # The tool did not change through all of the changeset revisions.
            return old_id

    def get_query_for_setting_metadata_on_repositories( self, my_writable=False, order=True ):
        """
        Return a query containing repositories for resetting metadata.  The order parameter
        is used for displaying the list of repositories ordered alphabetically for display on
        a page.  When called from the Tool Shed API, order is False.
        """
        # When called from the Tool Shed API, the metadata is reset on all repositories of types
        # repository_suite_definition and tool_dependency_definition in addition to other selected
        # repositories.
        if my_writable:
            username = self.user.username
            clause_list = []
            for repository in self.sa_session.query( self.app.model.Repository ) \
                                             .filter( self.app.model.Repository.table.c.deleted == False ):
                # Always reset metadata on all repositories of types repository_suite_definition and
                # tool_dependency_definition.
                if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION, rt_util.TOOL_DEPENDENCY_DEFINITION ]:
                    clause_list.append( self.app.model.Repository.table.c.id == repository.id )
                else:
                    allow_push = repository.allow_push( self.app )
                    if allow_push:
                        # Include all repositories that are writable by the current user.
                        allow_push_usernames = allow_push.split( ',' )
                        if username in allow_push_usernames:
                            clause_list.append( self.app.model.Repository.table.c.id == repository.id )
            if clause_list:
                if order:
                    return self.sa_session.query( self.app.model.Repository ) \
                                          .filter( or_( *clause_list ) ) \
                                          .order_by( self.app.model.Repository.table.c.name,
                                                     self.app.model.Repository.table.c.user_id )
                else:
                    return self.sa_session.query( self.app.model.Repository ) \
                                          .filter( or_( *clause_list ) )
            else:
                # Return an empty query.
                return self.sa_session.query( self.app.model.Repository ) \
                                      .filter( self.app.model.Repository.table.c.id == -1 )
        else:
            if order:
                return self.sa_session.query( self.app.model.Repository ) \
                                      .filter( self.app.model.Repository.table.c.deleted == False ) \
                                      .order_by( self.app.model.Repository.table.c.name,
                                                 self.app.model.Repository.table.c.user_id )
            else:
                return self.sa_session.query( self.app.model.Repository ) \
                                      .filter( self.app.model.Repository.table.c.deleted == False )

    def get_skip_tool_test_by_changeset_revision( self, changeset_revision ):
        """
        Return a skip_tool_test record whose initial_changeset_revision is the received
        changeset_revision.
        """
        # There should only be one, but we'll use first() so callers won't have to handle exceptions.
        return self.sa_session.query( self.app.model.SkipToolTest ) \
                              .filter( self.app.model.SkipToolTest.table.c.initial_changeset_revision == changeset_revision ) \
                              .first()

    def new_datatypes_metadata_required( self, repository_metadata ):
        """
        Compare the last saved metadata for each datatype in the repository with the new metadata
        in self.metadata_dict to determine if a new repository_metadata table record is required
        or if the last saved metadata record can be updated for datatypes instead.
        """
        # Datatypes are stored in metadata as a list of dictionaries that looks like:
        # [{'dtype': 'galaxy.datatypes.data:Text', 'subclass': 'True', 'extension': 'acedb'}]
        if 'datatypes' in self.metadata_dict:
            current_datatypes = self.metadata_dict[ 'datatypes' ]
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'datatypes' in metadata:
                        ancestor_datatypes = metadata[ 'datatypes' ]
                        # The saved metadata must be a subset of the new metadata.
                        datatype_comparison = self.compare_datatypes( ancestor_datatypes, current_datatypes )
                        if datatype_comparison == self.NOT_EQUAL_AND_NOT_SUBSET:
                            return True
                        else:
                            return False
                    else:
                        # The new metadata includes datatypes, but the stored metadata does not,
                        # so we can update the stored metadata.
                        return False
                else:
                    # There is no stored metadata, so we can update the metadata column in the
                    # repository_metadata table.
                    return False
            else:
                # There is no stored repository metadata, so we need to create a new repository_metadata
                # table record.
                return True
        # self.metadata_dict includes no metadata for datatypes, so a new repository_metadata
        # table record is not needed.
        return False

    def new_metadata_required_for_utilities( self ):
        """
        This method compares the last stored repository_metadata record associated with self.repository
        against the contents of self.metadata_dict and returns True or False for the union set of Galaxy
        utilities contained in both metadata dictionaries.  The metadata contained in self.metadata_dict
        may not be a subset of that contained in the last stored repository_metadata record associated with
        self.repository because one or more Galaxy utilities may have been deleted from self.repository in
        the new tip.
        """
        repository_metadata = metadata_util.get_latest_repository_metadata( self.app,
                                                                            self.repository.id,
                                                                            downloadable=False )
        datatypes_required = self.new_datatypes_metadata_required( repository_metadata )
        # Uncomment the following if we decide that README files should affect how installable
        # repository revisions are defined.  See the NOTE in the compare_readme_files() method.
        # readme_files_required = sewlf.new_readme_files_metadata_required( repository_metadata )
        repository_dependencies_required = \
            self.new_repository_dependency_metadata_required( repository_metadata )
        tools_required = self.new_tool_metadata_required( repository_metadata )
        tool_dependencies_required = self.new_tool_dependency_metadata_required( repository_metadata )
        workflows_required = self.new_workflow_metadata_required( repository_metadata )
        if datatypes_required or \
            repository_dependencies_required or \
            tools_required or \
            tool_dependencies_required or \
            workflows_required:
            return True
        return False

    def new_readme_files_metadata_required( self, repository_metadata ):
        """
        Compare the last saved metadata for each readme file in the repository with the new metadata
        in self.metadata_dict to determine if a new repository_metadata table record is required or
        if the last saved metadata record can be updated for readme files instead.
        """
        # Repository README files are kind of a special case because they have no effect on reproducibility.
        # We'll simply inspect the file names to determine if any that exist in the saved metadata are
        # eliminated from the new metadata in self.metadata_dict.
        if 'readme_files' in self.metadata_dict:
            current_readme_files = self.metadata_dict[ 'readme_files' ]
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'readme_files' in metadata:
                        ancestor_readme_files = metadata[ 'readme_files' ]
                        # The saved metadata must be a subset of the new metadata.
                        readme_file_comparison = self.compare_readme_files( ancestor_readme_files,
                                                                            current_readme_files )
                        if readme_file_comparison == self.NOT_EQUAL_AND_NOT_SUBSET:
                            return True
                        else:
                            return False
                    else:
                        # The new metadata includes readme_files, but the stored metadata does not, so
                        # we can update the stored metadata.
                        return False
                else:
                    # There is no stored metadata, so we can update the metadata column in the repository_metadata
                    # table.
                    return False
            else:
                # There is no stored repository metadata, so we need to create a new repository_metadata
                # table record.
                return True
        # self.metadata_dict includes no metadata for readme_files, so a new repository_metadata
        # table record is not needed.
        return False

    def new_repository_dependency_metadata_required( self, repository_metadata ):
        """
        Compare the last saved metadata for each repository dependency in the repository
        with the new metadata in self.metadata_dict to determine if a new repository_metadata
        table record is required or if the last saved metadata record can be updated for
        repository_dependencies instead.
        """
        if repository_metadata:
            metadata = repository_metadata.metadata
            if 'repository_dependencies' in metadata:
                saved_repository_dependencies = metadata[ 'repository_dependencies' ][ 'repository_dependencies' ]
                new_repository_dependencies_metadata = self.metadata_dict.get( 'repository_dependencies', None )
                if new_repository_dependencies_metadata:
                    new_repository_dependencies = self.metadata_dict[ 'repository_dependencies' ][ 'repository_dependencies' ]
                    # TODO: We used to include the following here to handle the case where repository
                    # dependency definitions were deleted.  However this erroneously returned True in
                    # cases where is should not have done so.  This usually occurred where multiple single
                    # files were uploaded when a single tarball should have been.  We need to implement
                    # support for handling deleted repository dependency definitions so that we can guarantee
                    # reproducibility, but we need to do it in a way that is better than the following.
                    # for new_repository_dependency in new_repository_dependencies:
                    #     if new_repository_dependency not in saved_repository_dependencies:
                    #         return True
                    # The saved metadata must be a subset of the new metadata.
                    for saved_repository_dependency in saved_repository_dependencies:
                        if saved_repository_dependency not in new_repository_dependencies:
                            # In some cases, the only difference between a dependency definition in the lists
                            # is the changeset_revision value.  We'll check to see if this is the case, and if
                            # the defined dependency is a repository that has metadata set only on its tip.
                            if not self.different_revision_defines_tip_only_repository_dependency( saved_repository_dependency,
                                                                                                   new_repository_dependencies ):
                                return True
                    return False
                else:
                    # The repository_dependencies.xml file must have been deleted, so create a new
                    # repository_metadata record so we always have access to the deleted file.
                    return True
            else:
                return False
        else:
            if 'repository_dependencies' in self.metadata_dict:
                # There is no saved repository metadata, so we need to create a new repository_metadata record.
                return True
            else:
                # self.metadata_dict includes no metadata for repository dependencies, so a new repository_metadata
                # record is not needed.
                return False

    def new_tool_metadata_required( self, repository_metadata ):
        """
        Compare the last saved metadata for each tool in the repository with the new metadata in
        self.metadata_dict to determine if a new repository_metadata table record is required, or if
        the last saved metadata record can be updated instead.
        """
        if 'tools' in self.metadata_dict:
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'tools' in metadata:
                        saved_tool_ids = []
                        # The metadata for one or more tools was successfully generated in the past
                        # for this repository, so we first compare the version string for each tool id
                        # in self.metadata_dict with what was previously saved to see if we need to create
                        # a new table record or if we can simply update the existing record.
                        for new_tool_metadata_dict in self.metadata_dict[ 'tools' ]:
                            for saved_tool_metadata_dict in metadata[ 'tools' ]:
                                if saved_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                                    saved_tool_ids.append( saved_tool_metadata_dict[ 'id' ] )
                                if new_tool_metadata_dict[ 'id' ] == saved_tool_metadata_dict[ 'id' ]:
                                    if new_tool_metadata_dict[ 'version' ] != saved_tool_metadata_dict[ 'version' ]:
                                        return True
                        # So far, a new metadata record is not required, but we still have to check to see if
                        # any new tool ids exist in self.metadata_dict that are not in the saved metadata.  We do
                        # this because if a new tarball was uploaded to a repository that included tools, it
                        # may have removed existing tool files if they were not included in the uploaded tarball.
                        for new_tool_metadata_dict in self.metadata_dict[ 'tools' ]:
                            if new_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                                return True
                        return False
                    else:
                        # The new metadata includes tools, but the stored metadata does not, so we can
                        # update the stored metadata.
                        return False
                else:
                    # There is no stored metadata, so we can update the metadata column in the
                    # repository_metadata table.
                    return False
            else:
                # There is no stored repository metadata, so we need to create a new repository_metadata
                # table record.
                return True
        # self.metadata_dict includes no metadata for tools, so a new repository_metadata table
        # record is not needed.
        return False

    def new_tool_dependency_metadata_required( self, repository_metadata ):
        """
        Compare the last saved metadata for each tool dependency in the repository with the new
        metadata in self.metadata_dict to determine if a new repository_metadata table record is
        required or if the last saved metadata record can be updated for tool_dependencies instead.
        """
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if 'tool_dependencies' in metadata:
                    saved_tool_dependencies = metadata[ 'tool_dependencies' ]
                    new_tool_dependencies = self.metadata_dict.get( 'tool_dependencies', None )
                    if new_tool_dependencies:
                        # TODO: We used to include the following here to handle the case where
                        # tool dependency definitions were deleted.  However, this erroneously
                        # returned True in cases where is should not have done so.  This usually
                        # occurred where multiple single files were uploaded when a single tarball
                        # should have been.  We need to implement support for handling deleted
                        # tool dependency definitions so that we can guarantee reproducibility,
                        # but we need to do it in a way that is better than the following.
                        # for new_tool_dependency in new_tool_dependencies:
                        #     if new_tool_dependency not in saved_tool_dependencies:
                        #         return True
                        # The saved metadata must be a subset of the new metadata.
                        for saved_tool_dependency in saved_tool_dependencies:
                            if saved_tool_dependency not in new_tool_dependencies:
                                return True
                        return False
                    else:
                        # The tool_dependencies.xml file must have been deleted, so create a new
                        # repository_metadata record so we always have
                        # access to the deleted file.
                        return True
                else:
                    return False
            else:
                # We have repository metadata that does not include metadata for any tool dependencies
                # in the repository, so we can update the existing repository metadata.
                return False
        else:
            if 'tool_dependencies' in self.metadata_dict:
                # There is no saved repository metadata, so we need to create a new repository_metadata
                # record.
                return True
            else:
                # self.metadata_dict includes no metadata for tool dependencies, so a new repository_metadata
                # record is not needed.
                return False

    def new_workflow_metadata_required( self, repository_metadata ):
        """
        Currently everything about an exported workflow except the name is hard-coded, so
        there's no real way to differentiate versions of exported workflows.  If this changes
        at some future time, this method should be enhanced accordingly.
        """
        if 'workflows' in self.metadata_dict:
            if repository_metadata:
                # The repository has metadata, so update the workflows value -
                # no new record is needed.
                return False
            else:
                # There is no saved repository metadata, so we need to create a
                # new repository_metadata table record.
                return True
        # self.metadata_dict includes no metadata for workflows, so a new
        # repository_metadata table record is not needed.
        return False

    def reset_all_metadata_on_repository_in_tool_shed( self ):
        """Reset all metadata on a single repository in a tool shed."""    
        log.debug( "Resetting all metadata on repository: %s" % self.repository.name )
        repo = hg_util.get_repo_for_repository( self.app,
                                                repository=None,
                                                repo_path=self.repository.repo_path( self.app ),
                                                create=False )
        # The list of changeset_revisions refers to repository_metadata records that have been created
        # or updated.  When the following loop completes, we'll delete all repository_metadata records
        # for this repository that do not have a changeset_revision value in this list.
        changeset_revisions = []
        # When a new repository_metadata record is created, it always uses the values of
        # metadata_changeset_revision and metadata_dict.
        metadata_changeset_revision = None
        metadata_dict = None
        ancestor_changeset_revision = None
        ancestor_metadata_dict = None
        for changeset in self.repository.get_changesets_for_setting_metadata( self.app ):
            work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-ramorits" )
            ctx = repo.changectx( changeset )
            log.debug( "Cloning repository changeset revision: %s", str( ctx.rev() ) )
            cloned_ok, error_message = hg_util.clone_repository( self.repository_clone_url, work_dir, str( ctx.rev() ) )
            if cloned_ok:
                log.debug( "Generating metadata for changset revision: %s", str( ctx.rev() ) )
                self.set_changeset_revision( str( repo.changectx( changeset ) ) )
                self.set_relative_install_dir( work_dir )
                self.set_repository_files_dir( work_dir )
                self.generate_metadata_for_changeset_revision()
                if self.metadata_dict:
                    if metadata_changeset_revision is None and metadata_dict is None:
                        # We're at the first change set in the change log.
                        metadata_changeset_revision = self.changeset_revision
                        metadata_dict = self.metadata_dict
                    if ancestor_changeset_revision:
                        # Compare metadata from ancestor and current.  The value of comparison will be one of:
                        # self.NO_METADATA - no metadata for either ancestor or current, so continue from current
                        # self.EQUAL - ancestor metadata is equivalent to current metadata, so continue from current
                        # self.SUBSET - ancestor metadata is a subset of current metadata, so continue from current
                        # self.NOT_EQUAL_AND_NOT_SUBSET - ancestor metadata is neither equal to nor a subset of current
                        # metadata, so persist ancestor metadata.
                        comparison = self.compare_changeset_revisions( ancestor_changeset_revision, ancestor_metadata_dict )
                        if comparison in [ self.NO_METADATA, self.EQUAL, self.SUBSET ]:
                            ancestor_changeset_revision = self.changeset_revision
                            ancestor_metadata_dict = self.metadata_dict
                        elif comparison == self.NOT_EQUAL_AND_NOT_SUBSET:
                            metadata_changeset_revision = ancestor_changeset_revision
                            metadata_dict = ancestor_metadata_dict
                            repository_metadata = self.create_or_update_repository_metadata( metadata_changeset_revision, metadata_dict )
                            changeset_revisions.append( metadata_changeset_revision )
                            ancestor_changeset_revision = self.changeset_revision
                            ancestor_metadata_dict = self.metadata_dict
                    else:
                        # We're at the beginning of the change log.
                        ancestor_changeset_revision = self.changeset_revision
                        ancestor_metadata_dict = self.metadata_dict
                    if not ctx.children():
                        metadata_changeset_revision = self.changeset_revision
                        metadata_dict = self.metadata_dict
                        # We're at the end of the change log.
                        repository_metadata = self.create_or_update_repository_metadata( metadata_changeset_revision, metadata_dict )
                        changeset_revisions.append( metadata_changeset_revision )
                        ancestor_changeset_revision = None
                        ancestor_metadata_dict = None
                elif ancestor_metadata_dict:
                    # We reach here only if self.metadata_dict is empty and ancestor_metadata_dict is not.
                    if not ctx.children():
                        # We're at the end of the change log.
                        repository_metadata = self.create_or_update_repository_metadata( metadata_changeset_revision, metadata_dict )
                        changeset_revisions.append( metadata_changeset_revision )
                        ancestor_changeset_revision = None
                        ancestor_metadata_dict = None
            basic_util.remove_dir( work_dir )
        # Delete all repository_metadata records for this repository that do not have a changeset_revision
        # value in changeset_revisions.
        self.clean_repository_metadata( changeset_revisions )
        # Set tool version information for all downloadable changeset revisions.  Get the list of changeset
        # revisions from the changelog.
        self.reset_all_tool_versions( repo )
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        self.app.tool_data_tables.data_tables = {}

    def reset_all_tool_versions( self, repo ):
        """Reset tool version lineage for those changeset revisions that include valid tools."""
        encoded_repository_id = self.app.security.encode_id( self.repository.id )
        changeset_revisions_that_contain_tools = []
        for changeset in repo.changelog:
            changeset_revision = str( repo.changectx( changeset ) )
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app,
                                                                                     encoded_repository_id,
                                                                                     changeset_revision )
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if metadata.get( 'tools', None ):
                        changeset_revisions_that_contain_tools.append( changeset_revision )
        # The list of changeset_revisions_that_contain_tools is now filtered to contain only those that
        # are downloadable and contain tools.  If a repository includes tools, build a dictionary of
        # { 'tool id' : 'parent tool id' } pairs for each tool in each changeset revision.
        for index, changeset_revision in enumerate( changeset_revisions_that_contain_tools ):
            tool_versions_dict = {}
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( self.app,
                                                                                     encoded_repository_id,
                                                                                     changeset_revision )
            metadata = repository_metadata.metadata
            tool_dicts = metadata[ 'tools' ]
            if index == 0:
                # The first changeset_revision is a special case because it will have no ancestor
                # changeset_revisions in which to match tools.  The parent tool id for tools in the
                # first changeset_revision will be the "old_id" in the tool config.
                for tool_dict in tool_dicts:
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = tool_dict[ 'id' ]
            else:
                for tool_dict in tool_dicts:
                    parent_id = self.get_parent_id( encoded_repository_id,
                                                    tool_dict[ 'id' ],
                                                    tool_dict[ 'version' ],
                                                    tool_dict[ 'guid' ],
                                                    changeset_revisions_that_contain_tools[ 0:index ] )
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
            if tool_versions_dict:
                repository_metadata.tool_versions = tool_versions_dict
                self.sa_session.add( repository_metadata )
                self.sa_session.flush()

    def reset_metadata_on_selected_repositories( self, **kwd ):
        """
        Inspect the repository changelog to reset metadata for all appropriate changeset revisions.
        This method is called from both Galaxy and the Tool Shed.
        """
        repository_ids = util.listify( kwd.get( 'repository_ids', None ) )
        message = ''
        status = 'done'
        if repository_ids:
            successful_count = 0
            unsuccessful_count = 0
            for repository_id in repository_ids:
                try:
                    repository = suc.get_repository_in_tool_shed( self.app, repository_id )
                    self.set_repository( repository )
                    self.reset_all_metadata_on_repository_in_tool_shed()
                    if self.invalid_file_tups:
                        message = tool_util.generate_message_for_invalid_tools( self.app,
                                                                                self.invalid_file_tups,
                                                                                repository,
                                                                                None,
                                                                                as_html=False )
                        log.debug( message )
                        unsuccessful_count += 1
                    else:
                        log.debug( "Successfully reset metadata on repository %s owned by %s" % \
                            ( str( repository.name ), str( repository.user.username ) ) )
                        successful_count += 1
                except:
                    log.exception( "Error attempting to reset metadata on repository %s" % str( repository.name ) )
                    unsuccessful_count += 1
            message = "Successfully reset metadata on %d %s.  " % \
                ( successful_count, inflector.cond_plural( successful_count, "repository" ) )
            if unsuccessful_count:
                message += "Error setting metadata on %d %s - see the paster log for details.  " % \
                    ( unsuccessful_count, inflector.cond_plural( unsuccessful_count, "repository" ) )
        else:
            message = 'Select at least one repository to on which to reset all metadata.'
            status = 'error'
        return message, status

    def set_repository( self, repository ):
        super( RepositoryMetadataManager, self ).set_repository( repository )
        self.repository_clone_url = common_util.generate_clone_url_for_repository_in_tool_shed( self.user, repository )

    def set_repository_metadata( self, host, content_alert_str='', **kwd ):
        """
        Set metadata using the self.repository's current disk files, returning specific error
        messages (if any) to alert the repository owner that the changeset has problems.
        """
        message = ''
        status = 'done'
        encoded_id = self.app.security.encode_id( self.repository.id )
        repo_dir = self.repository.repo_path( self.app )
        repo = hg_util.get_repo_for_repository( self.app, repository=None, repo_path=repo_dir, create=False )
        self.generate_metadata_for_changeset_revision()
        if self.metadata_dict:
            repository_metadata = None
            repository_type_class = self.app.repository_types_registry.get_class_by_label( self.repository.type )
            tip_only = isinstance( repository_type_class, TipOnly )
            if not tip_only and self.new_metadata_required_for_utilities():
                # Create a new repository_metadata table row.
                repository_metadata = self.create_or_update_repository_metadata( self.repository.tip( self.app ),
                                                                                 self.metadata_dict )
                # If this is the first record stored for this repository, see if we need to send any email alerts.
                if len( self.repository.downloadable_revisions ) == 1:
                    suc.handle_email_alerts( self.app,
                                             host,
                                             self.repository,
                                             content_alert_str='',
                                             new_repo_alert=True,
                                             admin_only=False )
            else:
                # Update the latest stored repository metadata with the contents and attributes of self.metadata_dict.
                repository_metadata = metadata_util.get_latest_repository_metadata( self.app,
                                                                                    self.repository.id,
                                                                                    downloadable=False )
                if repository_metadata:
                    downloadable = metadata_util.is_downloadable( self.metadata_dict )
                    # Update the last saved repository_metadata table row.
                    repository_metadata.changeset_revision = self.repository.tip( self.app )
                    repository_metadata.metadata = self.metadata_dict
                    repository_metadata.downloadable = downloadable
                    if 'datatypes' in self.metadata_dict:
                        repository_metadata.includes_datatypes = True
                    else:
                        repository_metadata.includes_datatypes = False
                    # We don't store information about the special type of repository dependency that is needed only for
                    # compiling a tool dependency defined for the dependent repository.
                    repository_dependencies_dict = self.metadata_dict.get( 'repository_dependencies', {} )
                    repository_dependencies = repository_dependencies_dict.get( 'repository_dependencies', [] )
                    has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td = \
                        suc.get_repository_dependency_types( repository_dependencies )
                    repository_metadata.has_repository_dependencies = has_repository_dependencies
                    if 'tool_dependencies' in self.metadata_dict:
                        repository_metadata.includes_tool_dependencies = True
                    else:
                        repository_metadata.includes_tool_dependencies = False
                    if 'tools' in self.metadata_dict:
                        repository_metadata.includes_tools = True
                    else:
                        repository_metadata.includes_tools = False
                    if 'workflows' in self.metadata_dict:
                        repository_metadata.includes_workflows = True
                    else:
                        repository_metadata.includes_workflows = False
                    repository_metadata.do_not_test = False
                    repository_metadata.time_last_tested = None
                    repository_metadata.tools_functionally_correct = False
                    repository_metadata.missing_test_components = False
                    repository_metadata.tool_test_results = None
                    self.sa_session.add( repository_metadata )
                    self.sa_session.flush()
                else:
                    # There are no metadata records associated with the repository.
                    repository_metadata = self.create_or_update_repository_metadata( self.repository.tip( self.app ),
                                                                                     self.metadata_dict )
            if 'tools' in self.metadata_dict and repository_metadata and status != 'error':
                # Set tool versions on the new downloadable change set.  The order of the list of changesets is
                # critical, so we use the repo's changelog.
                changeset_revisions = []
                for changeset in repo.changelog:
                    changeset_revision = str( repo.changectx( changeset ) )
                    if suc.get_repository_metadata_by_changeset_revision( self.app, encoded_id, changeset_revision ):
                        changeset_revisions.append( changeset_revision )
                self.add_tool_versions( encoded_id, repository_metadata, changeset_revisions )
        elif len( repo ) == 1 and not self.invalid_file_tups:
            message = "Revision <b>%s</b> includes no Galaxy utilities for which metadata can " % \
                str( self.repository.tip( self.app ) )
            message += "be defined so this revision cannot be automatically installed into a local Galaxy instance."
            status = "error"
        if self.invalid_file_tups:
            message = tool_util.generate_message_for_invalid_tools( self.app,
                                                                    self.invalid_file_tups,
                                                                    self.repository,
                                                                    self.metadata_dict )
            status = 'error'
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        self.app.tool_data_tables.data_tables = {}
        return message, status

    def set_repository_metadata_due_to_new_tip( self, host, content_alert_str=None, **kwd ):
        """Set metadata on the tip of self.repository in the tool shed."""
        error_message, status = self.set_repository_metadata( host, content_alert_str=content_alert_str, **kwd )
        return status, error_message
