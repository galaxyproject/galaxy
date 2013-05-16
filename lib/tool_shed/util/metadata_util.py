import logging
import os
import tempfile
from galaxy import eggs
from galaxy import util
from galaxy import web
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.tools.data_manager.manager import DataManager
from galaxy.util import inflector
from galaxy.util import json
from galaxy.web import url_for
from galaxy.webapps.tool_shed.util import container_util
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import common_install_util
from tool_shed.util import readme_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util

import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree import ElementInclude

log = logging.getLogger( __name__ )

REPOSITORY_DATA_MANAGER_CONFIG_FILENAME = "data_manager_conf.xml"
NOT_TOOL_CONFIGS = [ 'datatypes_conf.xml', 'repository_dependencies.xml', 'tool_dependencies.xml', REPOSITORY_DATA_MANAGER_CONFIG_FILENAME ]

def add_tool_versions( trans, id, repository_metadata, changeset_revisions ):
    # Build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in repository_metadata.
    metadata = repository_metadata.metadata
    tool_versions_dict = {}
    for tool_dict in metadata.get( 'tools', [] ):
        # We have at least 2 changeset revisions to compare tool guids and tool ids.
        parent_id = get_parent_id( trans, id, tool_dict[ 'id' ], tool_dict[ 'version' ], tool_dict[ 'guid' ], changeset_revisions )
        tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
    if tool_versions_dict:
        repository_metadata.tool_versions = tool_versions_dict
        trans.sa_session.add( repository_metadata )
        trans.sa_session.flush()

def clean_repository_metadata( trans, id, changeset_revisions ):
    # Delete all repository_metadata records associated with the repository that have a changeset_revision that is not in changeset_revisions.
    # We sometimes see multiple records with the same changeset revision value - no idea how this happens. We'll assume we can delete the older
    # records, so we'll order by update_time descending and delete records that have the same changeset_revision we come across later..
    changeset_revisions_checked = []
    for repository_metadata in trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                               .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ) \
                                               .order_by( trans.model.RepositoryMetadata.table.c.changeset_revision,
                                                          trans.model.RepositoryMetadata.table.c.update_time.desc() ):
        changeset_revision = repository_metadata.changeset_revision
        if changeset_revision in changeset_revisions_checked or changeset_revision not in changeset_revisions:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()

def compare_changeset_revisions( ancestor_changeset_revision, ancestor_metadata_dict, current_changeset_revision, current_metadata_dict ):
    """Compare the contents of two changeset revisions to determine if a new repository metadata revision should be created."""
    # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.  This changeset_revision is an ancestor of
    # current_changeset_revision which is associated with current_metadata_dict.  A new repository_metadata record will be created only
    # when this method returns the string 'not equal and not subset'.
    ancestor_datatypes = ancestor_metadata_dict.get( 'datatypes', [] )
    ancestor_tools = ancestor_metadata_dict.get( 'tools', [] )
    ancestor_guids = [ tool_dict[ 'guid' ] for tool_dict in ancestor_tools ]
    ancestor_guids.sort()
    ancestor_readme_files = ancestor_metadata_dict.get( 'readme_files', [] )
    ancestor_repository_dependencies_dict = ancestor_metadata_dict.get( 'repository_dependencies', {} )
    ancestor_repository_dependencies = ancestor_repository_dependencies_dict.get( 'repository_dependencies', [] )
    ancestor_tool_dependencies = ancestor_metadata_dict.get( 'tool_dependencies', {} )
    ancestor_workflows = ancestor_metadata_dict.get( 'workflows', [] )
    current_datatypes = current_metadata_dict.get( 'datatypes', [] )
    current_tools = current_metadata_dict.get( 'tools', [] )
    current_guids = [ tool_dict[ 'guid' ] for tool_dict in current_tools ]
    current_guids.sort()
    current_readme_files = current_metadata_dict.get( 'readme_files', [] )
    current_repository_dependencies_dict = current_metadata_dict.get( 'repository_dependencies', {} )
    current_repository_dependencies = current_repository_dependencies_dict.get( 'repository_dependencies', [] )
    current_tool_dependencies = current_metadata_dict.get( 'tool_dependencies', {} ) 
    current_workflows = current_metadata_dict.get( 'workflows', [] )
    # Handle case where no metadata exists for either changeset.
    no_datatypes = not ancestor_datatypes and not current_datatypes
    no_readme_files = not ancestor_readme_files and not current_readme_files
    no_repository_dependencies = not ancestor_repository_dependencies and not current_repository_dependencies
    # Tool dependencies can define orphan dependencies in the tool shed.
    no_tool_dependencies = not ancestor_tool_dependencies and not current_tool_dependencies
    no_tools = not ancestor_guids and not current_guids
    no_workflows = not ancestor_workflows and not current_workflows
    if no_datatypes and no_readme_files and no_repository_dependencies and no_tool_dependencies and no_tools and no_workflows:
        return 'no metadata'
    # Uncomment the following if we decide that README files should affect how installable repository revisions are defined.  See the NOTE in the
    # compare_readme_files() method.
    # readme_file_comparision = compare_readme_files( ancestor_readme_files, current_readme_files )
    repository_dependency_comparison = compare_repository_dependencies( ancestor_repository_dependencies, current_repository_dependencies )
    tool_dependency_comparison = compare_tool_dependencies( ancestor_tool_dependencies, current_tool_dependencies )
    workflow_comparison = compare_workflows( ancestor_workflows, current_workflows )
    datatype_comparison = compare_datatypes( ancestor_datatypes, current_datatypes )
    # Handle case where all metadata is the same.
    if ancestor_guids == current_guids and \
        repository_dependency_comparison == 'equal' and \
        tool_dependency_comparison == 'equal' and \
        workflow_comparison == 'equal' and \
        datatype_comparison == 'equal':
        return 'equal'
    # Handle case where ancestor metadata is a subset of current metadata.
    # readme_file_is_subset = readme_file_comparision in [ 'equal', 'subset' ]
    repository_dependency_is_subset = repository_dependency_comparison in [ 'equal', 'subset' ]
    tool_dependency_is_subset = tool_dependency_comparison in [ 'equal', 'subset' ]
    workflow_dependency_is_subset = workflow_comparison in [ 'equal', 'subset' ]
    datatype_is_subset = datatype_comparison in [ 'equal', 'subset' ]
    if repository_dependency_is_subset and tool_dependency_is_subset and workflow_dependency_is_subset and datatype_is_subset:
        is_subset = True
        for guid in ancestor_guids:
            if guid not in current_guids:
                is_subset = False
                break
        if is_subset:
            return 'subset'
    return 'not equal and not subset'

def compare_datatypes( ancestor_datatypes, current_datatypes ):
    """Determine if ancestor_datatypes is the same as or a subset of current_datatypes."""
    # Each datatype dict looks something like: {"dtype": "galaxy.datatypes.images:Image", "extension": "pdf", "mimetype": "application/pdf"}
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
                return 'not equal and not subset'
        if len( ancestor_datatypes ) == len( current_datatypes ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'

def compare_readme_files( ancestor_readme_files, current_readme_files ):
    """Determine if ancestor_readme_files is equal to or a subset of current_readme_files."""
    # NOTE: Although repository README files are considered a Galaxy utility similar to tools, repository dependency definition files, etc.,
    # we don't define installable repository revisions based on changes to README files.  To understand why, consider the following scenario:
    # 1. Upload the filtering tool to a new repository - this will result in installable revision 0.
    # 2. Upload a README file to the repository - this will move the installable revision from revision 0 to revision 1.
    # 3. Delete the README file from the repository - this will move the installable revision from revision 1 to revision 2.
    # The above scenario is the current behavior, and that is why this method is not currently called.  This method exists only in case we decide
    # to change this current behavior.
    # The lists of readme files looks something like: ["database/community_files/000/repo_2/readme.txt"]
    if len( ancestor_readme_files ) <= len( current_readme_files ):
        for ancestor_readme_file in ancestor_readme_files:
            if ancestor_readme_file not in current_readme_files:
                return 'not equal and not subset'
        if len( ancestor_readme_files ) == len( current_readme_files ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'

def compare_repository_dependencies( ancestor_repository_dependencies, current_repository_dependencies ):
    """Determine if ancestor_repository_dependencies is the same as or a subset of current_repository_dependencies."""
    # The list of repository_dependencies looks something like: [["http://localhost:9009", "emboss_datatypes", "test", "ab03a2a5f407", False]].
    # Create a string from each tuple in the list for easier comparison.
    if len( ancestor_repository_dependencies ) <= len( current_repository_dependencies ):
        for ancestor_tup in ancestor_repository_dependencies:
            ancestor_tool_shed, ancestor_repository_name, ancestor_repository_owner, ancestor_changeset_revision, ancestor_prior_installation_required = ancestor_tup
            found_in_current = False
            for current_tup in current_repository_dependencies:
                current_tool_shed, current_repository_name, current_repository_owner, current_changeset_revision, current_prior_installation_required = current_tup
                if current_tool_shed == ancestor_tool_shed and \
                    current_repository_name == ancestor_repository_name and \
                    current_repository_owner == ancestor_repository_owner and \
                    current_changeset_revision == ancestor_changeset_revision and \
                    current_prior_installation_required == ancestor_prior_installation_required:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_repository_dependencies ) == len( current_repository_dependencies ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'

def compare_tool_dependencies( ancestor_tool_dependencies, current_tool_dependencies ):
    """Determine if ancestor_tool_dependencies is the same as or a subset of current_tool_dependencies."""
    # The tool_dependencies dictionary looks something like:
    # {'bwa/0.5.9': {'readme': 'some string', 'version': '0.5.9', 'type': 'package', 'name': 'bwa'}}
    if len( ancestor_tool_dependencies ) <= len( current_tool_dependencies ):
        for ancestor_td_key, ancestor_requirements_dict in ancestor_tool_dependencies.items():
            if ancestor_td_key in current_tool_dependencies:
                # The only values that could have changed between the 2 dictionaries are the "readme" or "type" values.  Changing the readme value
                # makes no difference.  Changing the type will change the installation process, but for now we'll assume it was a typo, so new metadata
                # shouldn't be generated.
                continue
            else:
                return 'not equal and not subset'
        # At this point we know that ancestor_tool_dependencies is at least a subset of current_tool_dependencies.
        if len( ancestor_tool_dependencies ) == len( current_tool_dependencies ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'

def compare_workflows( ancestor_workflows, current_workflows ):
    """Determine if ancestor_workflows is the same as current_workflows or if ancestor_workflows is a subset of current_workflows."""
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
                # Assume that if the name and number of steps are euqal, then the workflows are the same.  Of course, this may not be true...
                if current_workflow_dict[ 'name' ] == ancestor_workflow_name and len( current_workflow_dict[ 'steps' ] ) == num_ancestor_workflow_steps:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_workflows ) == len( current_workflows ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'

def create_or_update_repository_metadata( trans, id, repository, changeset_revision, metadata_dict ):
    """Create or update a repository_metadatqa record in the tool shed."""
    has_repository_dependencies = False
    includes_datatypes = False
    includes_tools = False
    includes_tool_dependencies = False
    includes_workflows = False
    if metadata_dict:
        if 'repository_dependencies' in metadata_dict:
            has_repository_dependencies = True
        if 'datatypes' in metadata_dict:
            includes_datatypes = True
        if 'tools' in metadata_dict:
            includes_tools = True
        if 'tool_dependencies' in metadata_dict:
            includes_tool_dependencies = True
        if 'workflows' in metadata_dict:
            includes_workflows = True
    downloadable = has_repository_dependencies or includes_datatypes or includes_tools or includes_tool_dependencies or includes_workflows
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        # A repository metadata record already exists with the received changeset_revision, so we don't need to check the skip_tool_test table.
        check_skip_tool_test = False
        repository_metadata.metadata = metadata_dict
        repository_metadata.downloadable = downloadable
        repository_metadata.has_repository_dependencies = has_repository_dependencies
        repository_metadata.includes_datatypes = includes_datatypes
        repository_metadata.includes_tools = includes_tools
        repository_metadata.includes_tool_dependencies = includes_tool_dependencies
        repository_metadata.includes_workflows = includes_workflows
    else:
        # No repository_metadata record exists for the received changeset_revision, so we may need to update the skip_tool_test table.
        check_skip_tool_test = True
        repository_metadata = trans.model.RepositoryMetadata( repository_id=repository.id,
                                                              changeset_revision=changeset_revision,
                                                              metadata=metadata_dict,
                                                              downloadable=downloadable,
                                                              has_repository_dependencies=has_repository_dependencies,
                                                              includes_datatypes=includes_datatypes,
                                                              includes_tools=includes_tools,
                                                              includes_tool_dependencies=includes_tool_dependencies,
                                                              includes_workflows=includes_workflows )
    # Always set the default values for the following columns.  When resetting all metadata on a repository, this will reset the values.
    repository_metadata.tools_functionally_correct = False
    repository_metadata.missing_test_components = False
    repository_metadata.test_install_error = False
    repository_metadata.do_not_test = False
    repository_metadata.time_last_tested = None
    repository_metadata.tool_test_results = None
    trans.sa_session.add( repository_metadata )
    trans.sa_session.flush()
    if check_skip_tool_test:
        # Since we created a new repository_metadata record, we may need to update the skip_tool_test table to point to it.  Inspect each
        # changeset revision in the received repository's changelog (up to the received changeset revision) to see if it is contained in the
        # skip_tool_test table.  If it is, but is not associated with a repository_metadata record, reset that skip_tool_test record to the
        # newly created repository_metadata record.
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        for changeset in repo.changelog:
            changeset_hash = str( repo.changectx( changeset ) )
            skip_tool_test = suc.get_skip_tool_test_by_changeset_revision( trans, changeset_hash )
            if skip_tool_test:
                # We found a skip_tool_test record associated with the changeset_revision, so see if it has a valid repository_revision.
                repository_revision = suc.get_repository_metadata_by_id( trans, trans.security.encode_id( repository_metadata.id ) )
                if repository_revision:
                    # The skip_tool_test record is associated with a valid repository_metadata record, so proceed.
                    continue
                # We found a skip_tool_test record that is associated with an invalid repository_metadata record, so update it to point to
                # the newly created repository_metadata record.  In some special cases there may be multiple skip_tool_test records that
                # require updating, so we won't break here, we'll continue to inspect the rest of the changelog up to the received
                # changeset_revision.
                skip_tool_test.repository_metadata_id = repository_metadata.id
                trans.sa_session.add( skip_tool_test )
                trans.sa_session.flush()
            if changeset_hash == changeset_revision:
                # Proceed no further than the received changeset_revision.
                break
    return repository_metadata

def generate_data_manager_metadata( app, repository, repo_dir, data_manager_config_filename, metadata_dict, shed_config_dict=None ):
    """Update the received metadata_dict with information from the parsed data_manager_config_filename."""
    if data_manager_config_filename is None:
        return metadata_dict
    repo_path = repository.repo_path( app )
    try:
        # Galaxy Side.
        repo_files_directory = repository.repo_files_directory( app )
        repo_dir = repo_files_directory
        repository_clone_url = suc.generate_clone_url_for_installed_repository( app, repository )
    except AttributeError:
        # Tool Shed side.
        repo_files_directory = repo_path
        repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( None, repository )
    relative_data_manager_dir = util.relpath( os.path.split( data_manager_config_filename )[0], repo_dir )
    rel_data_manager_config_filename = os.path.join( relative_data_manager_dir, os.path.split( data_manager_config_filename )[1] )
    data_managers = {}
    invalid_data_managers = []
    data_manager_metadata = { 'config_filename': rel_data_manager_config_filename,
                              'data_managers': data_managers, 
                              'invalid_data_managers': invalid_data_managers, 
                              'error_messages': [] }
    metadata_dict[ 'data_manager' ] = data_manager_metadata
    try:
        tree = util.parse_xml( data_manager_config_filename )
    except Exception, e:
        # We are not able to load any data managers.
        error_message = 'There was an error parsing your Data Manager config file "%s": %s' % ( data_manager_config_filename, e )
        log.error( error_message )
        data_manager_metadata[ 'error_messages' ].append( error_message )
        return metadata_dict
    tool_path = None
    if shed_config_dict:
        tool_path = shed_config_dict.get( 'tool_path', None )
    tools = {}
    for tool in metadata_dict.get( 'tools', [] ):
        tool_conf_name = tool[ 'tool_config' ]
        if tool_path:
            tool_conf_name = os.path.join( tool_path, tool_conf_name )
        tools[ tool_conf_name ] = tool
    root = tree.getroot()
    data_manager_tool_path = root.get( 'tool_path', None )
    if data_manager_tool_path:
        relative_data_manager_dir = os.path.join( relative_data_manager_dir, data_manager_tool_path )
    for i, data_manager_elem in enumerate( root.findall( 'data_manager' ) ):
        tool_file = data_manager_elem.get( 'tool_file', None )
        data_manager_id = data_manager_elem.get( 'id', None )
        if data_manager_id is None:
            log.error( 'Data Manager entry is missing id attribute in "%s".' % ( data_manager_config_filename ) )
            invalid_data_managers.append( { 'index': i,
                                            'error_message': 'Data Manager entry is missing id attribute' } )
            continue
        # FIXME: default behavior is to fall back to tool.name.
        data_manager_name = data_manager_elem.get( 'name', data_manager_id )
        version = data_manager_elem.get( 'version', DataManager.DEFAULT_VERSION )
        guid = generate_guid_for_object( repository_clone_url, DataManager.GUID_TYPE, data_manager_id, version )
        data_tables = []
        if tool_file is None:
            log.error( 'Data Manager entry is missing tool_file attribute in "%s".' % ( data_manager_config_filename ) )
            invalid_data_managers.append( { 'index': i,
                                            'error_message': 'Data Manager entry is missing tool_file attribute' } )
            continue
        else:
            bad_data_table = False
            for data_table_elem in data_manager_elem.findall( 'data_table' ):
                data_table_name = data_table_elem.get( 'name', None )
                if data_table_name is None:
                    log.error( 'Data Manager data_table entry is missing name attribute in "%s".' % ( data_manager_config_filename ) )
                    invalid_data_managers.append( { 'index': i,
                                                    'error_message': 'Data Manager entry is missing name attribute' } )
                    bad_data_table = True
                    break
                else:
                    data_tables.append( data_table_name )
            if bad_data_table:
                continue
        data_manager_metadata_tool_file = os.path.normpath( os.path.join( relative_data_manager_dir, tool_file ) )
        tool_metadata_tool_file = os.path.join( repo_files_directory, data_manager_metadata_tool_file )
        tool = tools.get( tool_metadata_tool_file, None )
        if tool is None:
            log.error( "Unable to determine tools metadata for '%s'." % ( data_manager_metadata_tool_file ) )
            invalid_data_managers.append( { 'index': i,
                                            'error_message': 'Unable to determine tools metadata' } )
            continue
        data_managers[ data_manager_id ] = { 'id': data_manager_id, 
                                             'name': data_manager_name, 
                                             'guid': guid, 
                                             'version': version, 
                                             'tool_config_file': data_manager_metadata_tool_file, 
                                             'data_tables': data_tables, 
                                             'tool_guid': tool[ 'guid' ] }
        log.debug( 'Loaded Data Manager tool_files: %s' % ( tool_file ) )
    return metadata_dict

def generate_datatypes_metadata( app, repository, repository_clone_url, repository_files_dir, datatypes_config, metadata_dict ):
    """Update the received metadata_dict with information from the parsed datatypes_config."""
    try:
        tree = ElementTree.parse( datatypes_config )
    except Exception, e:
        log.debug( "Exception attempting to parse %s: %s" % ( str( datatypes_config ), str( e ) ) )
        return metadata_dict
    root = tree.getroot()
    ElementInclude.include( root )
    repository_datatype_code_files = []
    datatype_files = root.find( 'datatype_files' )
    if datatype_files:
        for elem in datatype_files.findall( 'datatype_file' ):
            name = elem.get( 'name', None )
            repository_datatype_code_files.append( name )
        metadata_dict[ 'datatype_files' ] = repository_datatype_code_files
    datatypes = []
    registration = root.find( 'registration' )
    if registration:
        for elem in registration.findall( 'datatype' ):
            converters = []
            display_app_containers = []
            datatypes_dict = {}
            # Handle defined datatype attributes.
            display_in_upload = elem.get( 'display_in_upload', None )
            if display_in_upload:
                datatypes_dict[ 'display_in_upload' ] = display_in_upload
            dtype = elem.get( 'type', None )
            if dtype:
                datatypes_dict[ 'dtype' ] = dtype
            extension = elem.get( 'extension', None )
            if extension:
                datatypes_dict[ 'extension' ] = extension
            max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
            if max_optional_metadata_filesize:
                datatypes_dict[ 'max_optional_metadata_filesize' ] = max_optional_metadata_filesize
            mimetype = elem.get( 'mimetype', None )
            if mimetype:
                datatypes_dict[ 'mimetype' ] = mimetype
            subclass = elem.get( 'subclass', None )
            if subclass:
                datatypes_dict[ 'subclass' ] = subclass
            # Handle defined datatype converters and display applications.
            for sub_elem in elem:
                if sub_elem.tag == 'converter':
                    # <converter file="bed_to_gff_converter.xml" target_datatype="gff"/>
                    tool_config = sub_elem.attrib[ 'file' ]
                    target_datatype = sub_elem.attrib[ 'target_datatype' ]
                    # Parse the tool_config to get the guid.
                    tool_config_path = suc.get_config_from_disk( tool_config, repository_files_dir )
                    full_path = os.path.abspath( tool_config_path )
                    tool, valid, error_message = tool_util.load_tool_from_config( app, app.security.encode_id( repository.id ), full_path )
                    if tool is None:
                        guid = None
                    else:
                        guid = suc.generate_tool_guid( repository_clone_url, tool )
                    converter_dict = dict( tool_config=tool_config,
                                           guid=guid,
                                           target_datatype=target_datatype )
                    converters.append( converter_dict )
                elif sub_elem.tag == 'display':
                    # <display file="ucsc/bigwig.xml" />
                    # Should we store more than this?
                    display_file = sub_elem.attrib[ 'file' ]
                    display_app_dict = dict( display_file=display_file )
                    display_app_containers.append( display_app_dict )
            if converters:
                datatypes_dict[ 'converters' ] = converters
            if display_app_containers:
                datatypes_dict[ 'display_app_containers' ] = display_app_containers
            if datatypes_dict:
                datatypes.append( datatypes_dict )
        if datatypes:
            metadata_dict[ 'datatypes' ] = datatypes
    return metadata_dict

def generate_environment_dependency_metadata( elem, valid_tool_dependencies_dict ):
    """
    The value of env_var_name must match the value of the "set_environment" type in the tool config's <requirements> tag set, or the tool dependency
    will be considered an orphan.  Tool dependencies of type set_environment are always defined as valid, but may be orphans.
    """
    # The value of the received elem looks something like this:
    # <set_environment version="1.0">
    #    <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
    # </set_environment>
    requirements_dict = {}
    for env_elem in elem:
        # <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
        env_name = env_elem.get( 'name', None )
        if env_name:
            requirements_dict[ 'name' ] = env_name
            requirements_dict[ 'type' ] = 'set_environment'
        if requirements_dict:
            if 'set_environment' in valid_tool_dependencies_dict:
                valid_tool_dependencies_dict[ 'set_environment' ].append( requirements_dict )
            else:
                valid_tool_dependencies_dict[ 'set_environment' ] = [ requirements_dict ]
    return valid_tool_dependencies_dict

def generate_guid_for_object( repository_clone_url, guid_type, obj_id, version ):
    tmp_url = suc.clean_repository_clone_url( repository_clone_url )
    return '%s/%s/%s/%s' % ( tmp_url, guid_type, obj_id, version )

def generate_metadata_for_changeset_revision( app, repository, changeset_revision, repository_clone_url, shed_config_dict=None, relative_install_dir=None,
                                              repository_files_dir=None, resetting_all_metadata_on_repository=False, updating_installed_repository=False,
                                              persist=False ):
    """
    Generate metadata for a repository using it's files on disk.  To generate metadata for changeset revisions older than the repository tip,
    the repository will have been cloned to a temporary location and updated to a specified changeset revision to access that changeset revision's
    disk files, so the value of repository_files_dir will not always be repository.repo_path( app ) (it could be an absolute path to a temporary
    directory containing a clone).  If it is an absolute path, the value of relative_install_dir must contain repository.repo_path( app ).
    
    The value of persist will be True when the installed repository contains a valid tool_data_table_conf.xml.sample file, in which case the entries
    should ultimately be persisted to the file referred to by app.config.shed_tool_data_table_config.
    """
    if shed_config_dict is None:
        shed_config_dict = {}
    if updating_installed_repository:
        # Keep the original tool shed repository metadata if setting metadata on a repository installed into a local Galaxy instance for which 
        # we have pulled updates.
        original_repository_metadata = repository.metadata
    else:
        original_repository_metadata = None
    readme_file_names = get_readme_file_names( repository.name )
    if app.name == 'galaxy':
        # Shed related tool panel configs are only relevant to Galaxy.
        metadata_dict = { 'shed_config_filename' : shed_config_dict.get( 'config_filename' ) }
    else:
        metadata_dict = {}
    readme_files = []
    invalid_file_tups = []
    invalid_tool_configs = []
    tool_dependencies_config = None
    original_tool_data_path = app.config.tool_data_path
    original_tool_data_table_config_path = app.config.tool_data_table_config_path
    if resetting_all_metadata_on_repository:
        if not relative_install_dir:
            raise Exception( "The value of repository.repo_path( app ) must be sent when resetting all metadata on a repository." )
        # Keep track of the location where the repository is temporarily cloned so that we can strip the path when setting metadata.  The value of
        # repository_files_dir is the full path to the temporary directory to which the repository was cloned.
        work_dir = repository_files_dir
        files_dir = repository_files_dir
        # Since we're working from a temporary directory, we can safely copy sample files included in the repository to the repository root.
        app.config.tool_data_path = repository_files_dir
        app.config.tool_data_table_config_path = repository_files_dir
    else:
        # Use a temporary working directory to copy all sample files.
        work_dir = tempfile.mkdtemp()
        # All other files are on disk in the repository's repo_path, which is the value of relative_install_dir.
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict[ 'tool_path' ], files_dir )
        app.config.tool_data_path = work_dir
        app.config.tool_data_table_config_path = work_dir
    # Handle proprietary datatypes, if any.
    datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', files_dir )
    if datatypes_config:
        metadata_dict = generate_datatypes_metadata( app, repository, repository_clone_url, files_dir, datatypes_config, metadata_dict )
    # Get the relative path to all sample files included in the repository for storage in the repository's metadata.
    sample_file_metadata_paths, sample_file_copy_paths = get_sample_files_from_disk( repository_files_dir=files_dir,
                                                                                     tool_path=shed_config_dict.get( 'tool_path' ),
                                                                                     relative_install_dir=relative_install_dir,
                                                                                     resetting_all_metadata_on_repository=resetting_all_metadata_on_repository )
    if sample_file_metadata_paths:
        metadata_dict[ 'sample_files' ] = sample_file_metadata_paths
    # Copy all sample files included in the repository to a single directory location so we can load tools that depend on them.
    for sample_file in sample_file_copy_paths:
        tool_util.copy_sample_file( app, sample_file, dest_path=work_dir )
        # If the list of sample files includes a tool_data_table_conf.xml.sample file, laad it's table elements into memory.
        relative_path, filename = os.path.split( sample_file )
        if filename == 'tool_data_table_conf.xml.sample':
            new_table_elems, error_message = app.tool_data_tables.add_new_entries_from_config_file( config_filename=sample_file,
                                                                                                    tool_data_path=app.config.tool_data_path,
                                                                                                    shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                                    persist=persist )
            if error_message:
                invalid_file_tups.append( ( filename, error_message ) )
    for root, dirs, files in os.walk( files_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # See if we have a repository dependencies defined.
                if name == 'repository_dependencies.xml':
                    path_to_repository_dependencies_config = os.path.join( root, name )
                    metadata_dict, error_message = generate_repository_dependency_metadata( app,  path_to_repository_dependencies_config, metadata_dict )
                    if error_message:
                        invalid_file_tups.append( ( name, error_message ) )
                # See if we have one or more READ_ME files.
                elif name.lower() in readme_file_names:
                    relative_path_to_readme = get_relative_path_to_repository_file( root,
                                                                                    name,
                                                                                    relative_install_dir,
                                                                                    work_dir,
                                                                                    shed_config_dict,
                                                                                    resetting_all_metadata_on_repository )
                    readme_files.append( relative_path_to_readme )
                # See if we have a tool config.
                elif name not in NOT_TOOL_CONFIGS and name.endswith( '.xml' ):
                    full_path = str( os.path.abspath( os.path.join( root, name ) ) )
                    if os.path.getsize( full_path ) > 0:
                        if not ( checkers.check_binary( full_path ) or checkers.check_image( full_path ) or checkers.check_gzip( full_path )[ 0 ]
                                 or checkers.check_bz2( full_path )[ 0 ] or checkers.check_zip( full_path ) ):
                            try:
                                # Make sure we're looking at a tool config and not a display application config or something else.
                                element_tree = util.parse_xml( full_path )
                                element_tree_root = element_tree.getroot()
                                is_tool = element_tree_root.tag == 'tool'
                            except Exception, e:
                                log.debug( "Error parsing %s, exception: %s" % ( full_path, str( e ) ) )
                                is_tool = False
                            if is_tool:
                                tool, valid, error_message = tool_util.load_tool_from_config( app, app.security.encode_id( repository.id ), full_path )
                                if tool is None:
                                    if not valid:
                                        invalid_tool_configs.append( name )
                                        invalid_file_tups.append( ( name, error_message ) )
                                else:
                                    invalid_files_and_errors_tups = tool_util.check_tool_input_params( app, files_dir, name, tool, sample_file_copy_paths )
                                    can_set_metadata = True
                                    for tup in invalid_files_and_errors_tups:
                                        if name in tup:
                                            can_set_metadata = False
                                            invalid_tool_configs.append( name )
                                            break
                                    if can_set_metadata:
                                        relative_path_to_tool_config = get_relative_path_to_repository_file( root,
                                                                                                             name,
                                                                                                             relative_install_dir,
                                                                                                             work_dir,
                                                                                                             shed_config_dict,
                                                                                                             resetting_all_metadata_on_repository )
                                        
                                        
                                        metadata_dict = generate_tool_metadata( relative_path_to_tool_config, tool, repository_clone_url, metadata_dict )
                                    else:
                                        for tup in invalid_files_and_errors_tups:
                                            invalid_file_tups.append( tup )
                # Find all exported workflows.
                elif name.endswith( '.ga' ):
                    relative_path = os.path.join( root, name )
                    if os.path.getsize( os.path.abspath( relative_path ) ) > 0:
                        fp = open( relative_path, 'rb' )
                        workflow_text = fp.read()
                        fp.close()
                        exported_workflow_dict = json.from_json_string( workflow_text )
                        if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                            metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    # Handle any data manager entries
    metadata_dict = generate_data_manager_metadata( app,
                                                    repository,
                                                    files_dir,
                                                    suc.get_config_from_disk( REPOSITORY_DATA_MANAGER_CONFIG_FILENAME, files_dir ),
                                                    metadata_dict,
                                                    shed_config_dict=shed_config_dict )
    
    if readme_files:
        metadata_dict[ 'readme_files' ] = readme_files
    # This step must be done after metadata for tools has been defined.
    tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', files_dir )
    if tool_dependencies_config:
        metadata_dict, error_message = generate_tool_dependency_metadata( app,
                                                                          repository,
                                                                          changeset_revision,
                                                                          repository_clone_url,
                                                                          tool_dependencies_config,
                                                                          metadata_dict,
                                                                          original_repository_metadata=original_repository_metadata )
        if error_message:
            invalid_file_tups.append( ( 'tool_dependencies.xml', error_message ) )
    if invalid_tool_configs:
        metadata_dict [ 'invalid_tools' ] = invalid_tool_configs
    # Reset the value of the app's tool_data_path  and tool_data_table_config_path to their respective original values.
    app.config.tool_data_path = original_tool_data_path
    app.config.tool_data_table_config_path = original_tool_data_table_config_path
    return metadata_dict, invalid_file_tups

def generate_package_dependency_metadata( app, elem, valid_tool_dependencies_dict, invalid_tool_dependencies_dict ):
    """
    Generate the metadata for a tool dependencies package defined for a repository.  The value of package_name must match the value of the "package"
    type in the tool config's <requirements> tag set.  This method is called from both Galaxy and the tool shed.
    """
    repository_dependency_is_valid = True
    repository_dependency_tup = []
    requirements_dict = {}
    error_message = ''
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if package_name and package_version:
        requirements_dict[ 'name' ] = package_name
        requirements_dict[ 'version' ] = package_version
        requirements_dict[ 'type' ] = 'package'
        for sub_elem in elem:
            if sub_elem.tag == 'readme':
                requirements_dict[ 'readme' ] = sub_elem.text
            elif sub_elem.tag == 'repository':
                # We have a complex repository dependency.  If the returned value of repository_dependency_is_valid is True, the tool
                # dependency definition will be set as invalid.  This is currently the only case where a tool dependency definition is
                # considered invalid.
                repository_dependency_tup, repository_dependency_is_valid, error_message = handle_repository_elem( app=app, repository_elem=sub_elem )
    if requirements_dict:
        dependency_key = '%s/%s' % ( package_name, package_version )
        if repository_dependency_is_valid:
            valid_tool_dependencies_dict[ dependency_key ] = requirements_dict
        else:
            # Append the error message to the requirements_dict.
            requirements_dict[ 'error' ] = error_message
            invalid_tool_dependencies_dict[ dependency_key ] = requirements_dict
    return valid_tool_dependencies_dict, invalid_tool_dependencies_dict, repository_dependency_tup, repository_dependency_is_valid, error_message

def generate_repository_dependency_metadata( app, repository_dependencies_config, metadata_dict ):
    """
    Generate a repository dependencies dictionary based on valid information defined in the received repository_dependencies_config.  This method
    is called from the tool shed as well as from Galaxy.
    """
    error_message = ''
    try:
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree = util.parse_xml( repository_dependencies_config )
        root = tree.getroot()
        xml_is_valid = root.tag == 'repositories'
    except Exception, e:
        error_message = "Error parsing %s, exception: %s" % ( repository_dependencies_config, str( e ) )
        log.debug( error_message )
        xml_is_valid = False
    if xml_is_valid:
        invalid_repository_dependencies_dict = dict( description=root.get( 'description' ) )
        invalid_repository_dependency_tups = []
        valid_repository_dependencies_dict = dict( description=root.get( 'description' ) )
        valid_repository_dependency_tups = []
        for repository_elem in root.findall( 'repository' ):
            repository_dependency_tup, repository_dependency_is_valid, error_message = handle_repository_elem( app, repository_elem )
            if repository_dependency_is_valid:
                valid_repository_dependency_tups.append( repository_dependency_tup )
            else:
                # Append the error_message to the repository dependencies tuple.
                toolshed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tup
                repository_dependency_tup = ( toolshed, name, owner, changeset_revision, prior_installation_required, error_message )
                invalid_repository_dependency_tups.append( repository_dependency_tup )
        if invalid_repository_dependency_tups:
            invalid_repository_dependencies_dict[ 'repository_dependencies' ] = invalid_repository_dependency_tups
            metadata_dict[ 'invalid_repository_dependencies' ] = invalid_repository_dependencies_dict
        if valid_repository_dependency_tups:
            valid_repository_dependencies_dict[ 'repository_dependencies' ] = valid_repository_dependency_tups
            metadata_dict[ 'repository_dependencies' ] = valid_repository_dependencies_dict
    return metadata_dict, error_message

def generate_tool_dependency_metadata( app, repository, changeset_revision, repository_clone_url, tool_dependencies_config, metadata_dict,
                                       original_repository_metadata=None ):
    """
    If the combination of name, version and type of each element is defined in the <requirement> tag for at least one tool in the repository,
    then update the received metadata_dict with information from the parsed tool_dependencies_config.
    """
    error_message = ''
    if original_repository_metadata:
        # Keep a copy of the original tool dependencies dictionary and the list of tool dictionaries in the metadata.
        original_valid_tool_dependencies_dict = original_repository_metadata.get( 'tool_dependencies', None )
        original_invalid_tool_dependencies_dict = original_repository_metadata.get( 'invalid_tool_dependencies', None )
    else:
        original_valid_tool_dependencies_dict = None
        original_invalid_tool_dependencies_dict = None
    try:
        tree = ElementTree.parse( tool_dependencies_config )
    except Exception, e:
        error_message = "Exception attempting to parse tool_dependencies.xml: %s" %str( e )
        log.debug( error_message )
        return metadata_dict, error_message
    root = tree.getroot()
    ElementInclude.include( root )
    tool_dependency_is_valid = True
    valid_tool_dependencies_dict = {}
    invalid_tool_dependencies_dict = {}
    valid_repository_dependency_tups = []
    invalid_repository_dependency_tups = []
    description = root.get( 'description' )
    for elem in root:
        if elem.tag == 'package':
            valid_tool_dependencies_dict, invalid_tool_dependencies_dict, repository_dependency_tup, repository_dependency_is_valid, message = \
                generate_package_dependency_metadata( app, elem, valid_tool_dependencies_dict, invalid_tool_dependencies_dict )
            if repository_dependency_is_valid:
                if repository_dependency_tup and repository_dependency_tup not in valid_repository_dependency_tups:
                    # We have a valid complex repository dependency.
                    valid_repository_dependency_tups.append( repository_dependency_tup )
            else:
                if repository_dependency_tup and repository_dependency_tup not in invalid_repository_dependency_tups:
                    # We have an invalid complex repository dependency, so mark the tool dependency as invalid.
                    tool_dependency_is_valid = False
                    # Append the error message to the invalid repository dependency tuple.
                    toolshed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tup
                    repository_dependency_tup = ( toolshed, name, owner, changeset_revision, prior_installation_required, message )
                    invalid_repository_dependency_tups.append( repository_dependency_tup )
                    error_message = '%s  %s' % ( error_message, message )
        elif elem.tag == 'set_environment':
            # Tool dependencies of this type are always considered valid, but may be orphans.
            valid_tool_dependencies_dict = generate_environment_dependency_metadata( elem, valid_tool_dependencies_dict )
    if valid_tool_dependencies_dict:
        if original_valid_tool_dependencies_dict:
            # We're generating metadata on an update pulled to a tool shed repository installed into a Galaxy instance, so handle changes to
            # tool dependencies appropriately.
            handle_existing_tool_dependencies_that_changed_in_update( app, repository, original_valid_tool_dependencies_dict, valid_tool_dependencies_dict )
        metadata_dict[ 'tool_dependencies' ] = valid_tool_dependencies_dict
    if invalid_tool_dependencies_dict:
        metadata_dict[ 'invalid_tool_dependencies' ] = invalid_tool_dependencies_dict
    if valid_repository_dependency_tups:
        metadata_dict = update_repository_dependencies_metadata( metadata=metadata_dict,
                                                                 repository_dependency_tups=valid_repository_dependency_tups,
                                                                 is_valid=True,
                                                                 description=description )
    if invalid_repository_dependency_tups:
        metadata_dict = update_repository_dependencies_metadata( metadata=metadata_dict,
                                                                 repository_dependency_tups=invalid_repository_dependency_tups,
                                                                 is_valid=False,
                                                                 description=description )
    # Determine and store orphan tool dependencies.
    orphan_tool_dependencies = get_orphan_tool_dependencies( metadata_dict )
    if orphan_tool_dependencies:
        metadata_dict[ 'orphan_tool_dependencies' ] = orphan_tool_dependencies
    return metadata_dict, error_message

def generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received tool."""
    # Generate the guid.
    guid = suc.generate_tool_guid( repository_clone_url, tool )
    # Handle tool.requirements.
    tool_requirements = []
    for tr in tool.requirements:
        requirement_dict = dict( name=tr.name,
                                 type=tr.type,
                                 version=tr.version )
        tool_requirements.append( requirement_dict )
    # Handle tool.tests.
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            required_files = []
            for required_file in ttb.required_files:
                value, extra = required_file
                required_files.append( ( value ) )
            inputs = []
            for input in ttb.inputs:
                name, value, extra = input
                inputs.append( ( name, value ) )
            outputs = []
            for output in ttb.outputs:
                name, file_name, extra = output
                outputs.append( ( name, suc.strip_path( file_name ) if file_name else None ) )
                if file_name not in required_files and file_name is not None:
                    required_files.append( file_name )
            test_dict = dict( name=ttb.name,
                              required_files=required_files,
                              inputs=inputs,
                              outputs=outputs )
            tool_tests.append( test_dict )
    # Determine if the tool should be loaded into the tool panel.  Examples of valid tools that should not be displayed in the tool panel are
    # datatypes converters and DataManager tools (which are of type 'manage_data').
    datatypes = metadata_dict.get( 'datatypes', None )
    add_to_tool_panel_attribute = set_add_to_tool_panel_attribute_for_tool( tool=tool, guid=guid, datatypes=datatypes )
    tool_dict = dict( id=tool.id,
                      guid=guid,
                      name=tool.name,
                      version=tool.version,
                      description=tool.description,
                      version_string_cmd = tool.version_string_cmd,
                      tool_config=tool_config,
                      tool_type=tool.tool_type,
                      requirements=tool_requirements,
                      tests=tool_tests,
                      add_to_tool_panel=add_to_tool_panel_attribute )
    if 'tools' in metadata_dict:
        metadata_dict[ 'tools' ].append( tool_dict )
    else:
        metadata_dict[ 'tools' ] = [ tool_dict ]
    return metadata_dict

def generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received exported_workflow_dict."""
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
    else:
        metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
    return metadata_dict

def get_latest_repository_metadata( trans, decoded_repository_id ):
    """Get last metadata defined for a specified repository from the database."""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == decoded_repository_id ) \
                           .order_by( trans.model.RepositoryMetadata.table.c.id.desc() ) \
                           .first()

def get_orphan_tool_dependencies( metadata ):
    """Inspect tool dependencies included in the received metadata and determine if any of them are orphans within the repository."""
    orphan_tool_dependencies_dict = {}
    if metadata:
        tools = metadata.get( 'tools', None )
        tool_dependencies = metadata.get( 'tool_dependencies', None )
        if tool_dependencies:
            for td_key, requirements_dict in tool_dependencies.items():
                if td_key in [ 'set_environment' ]:
                    for set_environment_dict in requirements_dict:
                        type = 'set_environment'
                        name = set_environment_dict.get( 'name', None )
                        version = None
                        if name:
                            if tool_dependency_is_orphan( type, name, version, tools ):
                                if td_key in orphan_tool_dependencies_dict:
                                    orphan_tool_dependencies_dict[ td_key ].append( set_environment_dict )
                                else:
                                    orphan_tool_dependencies_dict[ td_key ] = [ set_environment_dict ]
                else:
                    type = requirements_dict.get( 'type', None )
                    name = requirements_dict.get( 'name', None )
                    version = requirements_dict.get( 'version', None )
                    if type and name:
                        if tool_dependency_is_orphan( type, name, version, tools ):
                            orphan_tool_dependencies_dict[ td_key ] = requirements_dict
    return orphan_tool_dependencies_dict

def get_parent_id( trans, id, old_id, version, guid, changeset_revisions ):
    parent_id = None
    # Compare from most recent to oldest.
    changeset_revisions.reverse()
    for changeset_revision in changeset_revisions:
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
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

def get_readme_file_names( repository_name ):
    readme_files = [ 'readme', 'read_me', 'install' ]
    valid_filenames = [ r for r in readme_files ]
    for r in readme_files:
        valid_filenames.append( '%s.txt' % r )
    valid_filenames.append( '%s.txt' % repository_name )
    return valid_filenames

def get_relative_path_to_repository_file( root, name, relative_install_dir, work_dir, shed_config_dict, resetting_all_metadata_on_repository ):
    if resetting_all_metadata_on_repository:
        full_path_to_file = os.path.join( root, name )
        stripped_path_to_file = full_path_to_file.replace( work_dir, '' )
        if stripped_path_to_file.startswith( '/' ):
            stripped_path_to_file = stripped_path_to_file[ 1: ]
        relative_path_to_file = os.path.join( relative_install_dir, stripped_path_to_file )
    else:
        relative_path_to_file = os.path.join( root, name )
        if relative_install_dir and \
            shed_config_dict.get( 'tool_path' ) and relative_path_to_file.startswith( os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir ) ):
            relative_path_to_file = relative_path_to_file[ len( shed_config_dict.get( 'tool_path' ) ) + 1: ]
    return relative_path_to_file

def get_repository_metadata_by_id( trans, id ):
    """Get repository metadata from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ).get( trans.security.decode_id( id ) )

def get_repository_metadata_by_repository_id_changeset_revision( trans, id, changeset_revision ):
    """Get a specified metadata record for a specified repository."""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                           .first()

def get_repository_metadata_revisions_for_review( repository, reviewed=True ):
    repository_metadata_revisions = []
    metadata_changeset_revision_hashes = []
    if reviewed:
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append( metadata_revision.changeset_revision )
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                rmcr_hashes = [ rmr.changeset_revision for rmr in repository_metadata_revisions ]
                if review.changeset_revision not in rmcr_hashes:
                    repository_metadata_revisions.append( review.repository_metadata )
    else:
        for review in repository.reviews:
            if review.changeset_revision not in metadata_changeset_revision_hashes:
                metadata_changeset_revision_hashes.append( review.changeset_revision )
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( metadata_revision )
    return repository_metadata_revisions

def get_rev_label_changeset_revision_from_repository_metadata( trans, repository_metadata, repository=None ):
    if repository is None:
        repository = repository_metadata.repository
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    changeset_revision = repository_metadata.changeset_revision
    ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label, changeset_revision

def get_sample_files_from_disk( repository_files_dir, tool_path=None, relative_install_dir=None, resetting_all_metadata_on_repository=False ):
    if resetting_all_metadata_on_repository:
        # Keep track of the location where the repository is temporarily cloned so that we can strip it when setting metadata.
        work_dir = repository_files_dir
    sample_file_metadata_paths = []
    sample_file_copy_paths = []
    for root, dirs, files in os.walk( repository_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    if resetting_all_metadata_on_repository:
                        full_path_to_sample_file = os.path.join( root, name )
                        stripped_path_to_sample_file = full_path_to_sample_file.replace( work_dir, '' )
                        if stripped_path_to_sample_file.startswith( '/' ):
                            stripped_path_to_sample_file = stripped_path_to_sample_file[ 1: ]
                        relative_path_to_sample_file = os.path.join( relative_install_dir, stripped_path_to_sample_file )
                        if os.path.exists( relative_path_to_sample_file ):
                            sample_file_copy_paths.append( relative_path_to_sample_file )
                        else:
                            sample_file_copy_paths.append( full_path_to_sample_file )
                    else:
                        relative_path_to_sample_file = os.path.join( root, name )
                        sample_file_copy_paths.append( relative_path_to_sample_file )
                        if tool_path and relative_install_dir:
                            if relative_path_to_sample_file.startswith( os.path.join( tool_path, relative_install_dir ) ):
                                relative_path_to_sample_file = relative_path_to_sample_file[ len( tool_path ) + 1 :]
                        sample_file_metadata_paths.append( relative_path_to_sample_file )
    return sample_file_metadata_paths, sample_file_copy_paths

def get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Get all appropriate newer changeset revisions for the repository defined by the received tool_shed_url / name / owner combination.
    """
    url  = suc.url_join( tool_shed_url,
                         'repository/updated_changeset_revisions?name=%s&owner=%s&changeset_revision=%s' %
                         ( name, owner, changeset_revision ) )
    text = common_util.tool_shed_get( app, tool_shed_url, url )
    return text

def handle_existing_tool_dependencies_that_changed_in_update( app, repository, original_dependency_dict, new_dependency_dict ):
    """
    This method is called when a Galaxy admin is getting updates for an installed tool shed repository in order to cover the case where an
    existing tool dependency was changed (e.g., the version of the dependency was changed) but the tool version for which it is a dependency
    was not changed.  In this case, we only want to determine if any of the dependency information defined in original_dependency_dict was
    changed in new_dependency_dict.  We don't care if new dependencies were added in new_dependency_dict since they will just be treated as
    missing dependencies for the tool.
    """
    updated_tool_dependency_names = []
    deleted_tool_dependency_names = []
    for original_dependency_key, original_dependency_val_dict in original_dependency_dict.items():
        if original_dependency_key not in new_dependency_dict:
            updated_tool_dependency = update_existing_tool_dependency( app, repository, original_dependency_val_dict, new_dependency_dict )
            if updated_tool_dependency:
                updated_tool_dependency_names.append( updated_tool_dependency.name )
            else:
                deleted_tool_dependency_names.append( original_dependency_val_dict[ 'name' ] )
    return updated_tool_dependency_names, deleted_tool_dependency_names

def handle_repository_elem( app, repository_elem ):
    """
    Process the received repository_elem which is a <repository> tag either from a repository_dependencies.xml file or a tool_dependencies.xml file.
    If the former, we're generating repository dependencies metadata for a repository in the tool shed.  If the latter, we're generating package
    dependency metadata within Galaxy or the tool shed.
    """
    sa_session = app.model.context.current
    is_valid = True
    error_message = ''
    toolshed = repository_elem.get( 'toolshed' )
    if not toolshed:
        # Default to the current tool shed.
        toolshed = str( url_for( '/', qualified=True ) ).rstrip( '/' )
    name = repository_elem.get( 'name' )
    owner = repository_elem.get( 'owner' )
    changeset_revision = repository_elem.get( 'changeset_revision' )
    prior_installation_required = str( repository_elem.get( 'prior_installation_required', False ) )
    repository_dependency_tup = [ toolshed, name, owner, changeset_revision, prior_installation_required ]
    user = None
    repository = None
    if app.name == 'galaxy':
        # We're in Galaxy.  We reach here when we're generating the metadata for a tool dependencies package defined for a repository or when we're
        # generating metadata for an installed repository.  See if we can locate the installed repository via the changeset_revision defined in the
        # repository_elem (it may be outdated).  If we're successful in locating an installed repository with the attributes defined in the
        # repository_elem, we know it is valid.
        repository = suc.get_repository_for_dependency_relationship( app, toolshed, name, owner, changeset_revision )
        if repository:
            return repository_dependency_tup, is_valid, error_message
        else:
            # Send a request to the tool shed to retrieve appropriate additional changeset revisions with which the repository may have been installed.
            text = get_updated_changeset_revisions_from_tool_shed( app, toolshed, name, owner, changeset_revision )
            if text:
                updated_changeset_revisions = util.listify( text )
                for updated_changeset_revision in updated_changeset_revisions:
                    repository = suc.get_repository_for_dependency_relationship( app, toolshed, name, owner, updated_changeset_revision )
                    if repository:
                        return repository_dependency_tup, is_valid, error_message
            # We'll currently default to setting the repository dependency definition as invalid if an installed repository cannot be found.
            # This may not be ideal because the tool shed may have simply been inaccessible when metadata was being generated for the installed
            # tool shed repository.
            error_message = "Ignoring invalid repository dependency definition for tool shed %s, name %s, owner %s, changeset revision %s "% \
                ( toolshed, name, owner, changeset_revision )
            log.debug( error_message )
            is_valid = False
            return repository_dependency_tup, is_valid, error_message
    else:        
        # We're in the tool shed.
        if suc.tool_shed_is_this_tool_shed( toolshed ):
            try:
                user = sa_session.query( app.model.User ) \
                                 .filter( app.model.User.table.c.username == owner ) \
                                 .one()
            except Exception, e:                
                error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, changeset revision %s "% \
                    ( toolshed, name, owner, changeset_revision )
                error_message += "because the owner is invalid.  "
                log.debug( error_message )
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
            try:
                repository = sa_session.query( app.model.Repository ) \
                                       .filter( and_( app.model.Repository.table.c.name == name,
                                                      app.model.Repository.table.c.user_id == user.id ) ) \
                                       .one()
            except:
                error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, changeset revision %s "% \
                    ( toolshed, name, owner, changeset_revision )
                error_message += "because the name is invalid.  "
                log.debug( error_message )
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
            # Find the specified changeset revision in the repository's changelog to see if it's valid.
            found = False
            repo = hg.repository( suc.get_configured_ui(), repository.repo_path( app ) )
            for changeset in repo.changelog:
                changeset_hash = str( repo.changectx( changeset ) )
                if changeset_hash == changeset_revision:
                    found = True
                    break
            if not found:
                error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, changeset revision %s "% \
                    ( toolshed, name, owner, changeset_revision )
                error_message += "because the changeset revision is invalid.  "
                log.debug( error_message )
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
        else:
            # Repository dependencies are currently supported within a single tool shed.
            error_message = "Repository dependencies are currently supported only within the same tool shed.  Ignoring repository dependency definition "
            error_message += "for tool shed %s, name %s, owner %s, changeset revision %s.  " % ( toolshed, name, owner, changeset_revision )
            log.debug( error_message )
            is_valid = False
            return repository_dependency_tup, is_valid, error_message
    return repository_dependency_tup, is_valid, error_message

def is_downloadable( metadata_dict ):
    # NOTE: although repository README files are considered Galaxy utilities, they have no effect on determining if a revision is installable.
    # See the comments in the compare_readme_files() method.
    if 'datatypes' in metadata_dict:
        # We have proprietary datatypes.
        return True
    if 'repository_dependencies' in metadata_dict:
        # We have repository_dependencies.
        return True
    if 'tools' in metadata_dict:
        # We have tools.
        return True
    if 'tool_dependencies' in metadata_dict:
        # We have tool dependencies, and perhaps only tool dependencies!
        return True
    if 'workflows' in metadata_dict:
        # We have exported workflows.
        return True
    return False

def new_datatypes_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Compare the last saved metadata for each datatype in the repository with the new metadata in metadata_dict to determine if a new
    repository_metadata table record is required or if the last saved metadata record can be updated for datatypes instead.
    """
    # Datatypes are stored in metadata as a list of dictionaries that looks like:
    # [{'dtype': 'galaxy.datatypes.data:Text', 'subclass': 'True', 'extension': 'acedb'}]
    if 'datatypes' in metadata_dict:
        current_datatypes = metadata_dict[ 'datatypes' ]
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if 'datatypes' in metadata:
                    ancestor_datatypes = metadata[ 'datatypes' ]
                    # The saved metadata must be a subset of the new metadata.
                    datatype_comparison = compare_datatypes( ancestor_datatypes, current_datatypes )
                    if datatype_comparison == 'not equal and not subset':
                        return True
                    else:
                        return False
                else:
                    # The new metadata includes datatypes, but the stored metadata does not, so we can update the stored metadata.
                    return False
            else:
                # There is no stored metadata, so we can update the metadata column in the repository_metadata table.
                return False
        else:
            # There is no stored repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for datatypes, so a new repository_metadata table record is not needed.
    return False

def new_metadata_required_for_utilities( trans, repository, new_tip_metadata_dict ):
    """
    Galaxy utilities currently consist of datatypes, repository_dependency definitions, tools, tool_dependency definitions and exported
    Galaxy workflows.  This method compares the last stored repository_metadata record associated with the received repository against the
    contents of the received new_tip_metadata_dict and returns True or False for the union set of Galaxy utilities contained in both metadata
    dictionaries.  The metadata contained in new_tip_metadata_dict may not be a subset of that contained in the last stored repository_metadata
    record associated with the received repository because one or more Galaxy utilities may have been deleted from the repository in the new tip.
    """
    repository_metadata = get_latest_repository_metadata( trans, repository.id )
    datatypes_required = new_datatypes_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    # Uncomment the following if we decide that README files should affect how installable repository revisions are defined.  See the NOTE in the
    # compare_readme_files() method.
    # readme_files_required = new_readme_files_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    repository_dependencies_required = new_repository_dependency_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    tools_required = new_tool_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    tool_dependencies_required = new_tool_dependency_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    workflows_required = new_workflow_metadata_required( trans, repository_metadata, new_tip_metadata_dict )
    if datatypes_required or repository_dependencies_required or tools_required or tool_dependencies_required or workflows_required:
        return True
    return False

def new_readme_files_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Compare the last saved metadata for each readme file in the repository with the new metadata in metadata_dict to determine if a new
    repository_metadata table record is required or if the last saved metadata record can be updated for readme files instead.
    """
    # Repository README files are kind of a special case because they have no effect on reproducibility.  We'll simply inspect the file names to
    # determine if any that exist in the saved metadata are eliminated from the new metadata in the received metadata_dict.
    if 'readme_files' in metadata_dict:
        current_readme_files = metadata_dict[ 'readme_files' ]
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if 'readme_files' in metadata:
                    ancestor_readme_files = metadata[ 'readme_files' ]
                    # The saved metadata must be a subset of the new metadata.
                    readme_file_comparison = compare_readme_files( ancestor_readme_files, current_readme_files )
                    if readme_file_comparison == 'not equal and not subset':
                        return True
                    else:
                        return False
                else:
                    # The new metadata includes readme_files, but the stored metadata does not, so we can update the stored metadata.
                    return False
            else:
                # There is no stored metadata, so we can update the metadata column in the repository_metadata table.
                return False
        else:
            # There is no stored repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for readme_files, so a new repository_metadata table record is not needed.
    return False

def new_repository_dependency_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Compare the last saved metadata for each repository dependency in the repository with the new metadata in metadata_dict to determine if a new
    repository_metadata table record is required or if the last saved metadata record can be updated for repository_dependencies instead.
    """
    if repository_metadata:
        metadata = repository_metadata.metadata
        if 'repository_dependencies' in metadata:
            saved_repository_dependencies = metadata[ 'repository_dependencies' ][ 'repository_dependencies' ]
            new_repository_dependencies_metadata = metadata_dict.get( 'repository_dependencies', None )
            if new_repository_dependencies_metadata:
                new_repository_dependencies = metadata_dict[ 'repository_dependencies' ][ 'repository_dependencies' ]
                # The saved metadata must be a subset of the new metadata.
                for saved_repository_dependency in saved_repository_dependencies:
                    if saved_repository_dependency not in new_repository_dependencies:
                        return True
                return False
            else:
                # The repository_dependencies.xml file must have been deleted, so create a new repository_metadata record so we always have
                # access to the deleted file.
                return True
        else:
            return False
    else:
        if 'repository_dependencies' in metadata_dict:
            # There is no saved repository metadata, so we need to create a new repository_metadata record.
            return True
        else:
            # The received metadata_dict includes no metadata for repository dependencies, so a new repository_metadata record is not needed.
            return False

def new_tool_dependency_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Compare the last saved metadata for each tool dependency in the repository with the new metadata in metadata_dict to determine if a new
    repository_metadata table record is required or if the last saved metadata record can be updated for tool_dependencies instead.
    """
    if repository_metadata:
        metadata = repository_metadata.metadata
        if metadata:
            if 'tool_dependencies' in metadata:
                saved_tool_dependencies = metadata[ 'tool_dependencies' ]
                new_tool_dependencies = metadata_dict.get( 'tool_dependencies', None )
                if new_tool_dependencies:
                    # The saved metadata must be a subset of the new metadata.
                    for saved_tool_dependency in saved_tool_dependencies:
                        if saved_tool_dependency not in new_tool_dependencies:
                            return True
                    return False
                else:
                    # The tool_dependencies.xml file must have been deleted, so create a new repository_metadata record so we always have
                    # access to the deleted file.
                    return True
            else:
                return False
        else:
            # We have repository metadata that does not include metadata for any tool dependencies in the repository, so we can update
            # the existing repository metadata.
            return False
    else:
        if 'tool_dependencies' in metadata_dict:
            # There is no saved repository metadata, so we need to create a new repository_metadata record.
            return True
        else:
            # The received metadata_dict includes no metadata for tool dependencies, so a new repository_metadata record is not needed.
            return False

def new_tool_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Compare the last saved metadata for each tool in the repository with the new metadata in metadata_dict to determine if a new repository_metadata
    table record is required, or if the last saved metadata record can be updated instead.
    """
    if 'tools' in metadata_dict:
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if 'tools' in metadata:
                    saved_tool_ids = []
                    # The metadata for one or more tools was successfully generated in the past
                    # for this repository, so we first compare the version string for each tool id
                    # in metadata_dict with what was previously saved to see if we need to create
                    # a new table record or if we can simply update the existing record.
                    for new_tool_metadata_dict in metadata_dict[ 'tools' ]:
                        for saved_tool_metadata_dict in metadata[ 'tools' ]:
                            if saved_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                                saved_tool_ids.append( saved_tool_metadata_dict[ 'id' ] )
                            if new_tool_metadata_dict[ 'id' ] == saved_tool_metadata_dict[ 'id' ]:
                                if new_tool_metadata_dict[ 'version' ] != saved_tool_metadata_dict[ 'version' ]:
                                    return True
                    # So far, a new metadata record is not required, but we still have to check to see if
                    # any new tool ids exist in metadata_dict that are not in the saved metadata.  We do
                    # this because if a new tarball was uploaded to a repository that included tools, it
                    # may have removed existing tool files if they were not included in the uploaded tarball.
                    for new_tool_metadata_dict in metadata_dict[ 'tools' ]:
                        if new_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                            return True
                    return False
                else:
                    # The new metadata includes tools, but the stored metadata does not, so we can update the stored metadata.
                    return False
            else:
                # There is no stored metadata, so we can update the metadata column in the repository_metadata table.
                return False
        else:
            # There is no stored repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for tools, so a new repository_metadata table record is not needed.
    return False

def new_workflow_metadata_required( trans, repository_metadata, metadata_dict ):
    """
    Currently everything about an exported workflow except the name is hard-coded, so there's no real way to differentiate versions of
    exported workflows.  If this changes at some future time, this method should be enhanced accordingly.
    """
    if 'workflows' in metadata_dict:
        if repository_metadata:
            # The repository has metadata, so update the workflows value - no new record is needed.
            return False
        else:
            # There is no saved repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for workflows, so a new repository_metadata table record is not needed.
    return False

def populate_containers_dict_from_repository_metadata( trans, tool_shed_url, tool_path, repository, reinstalling=False, required_repo_info_dicts=None ):
    """
    Retrieve necessary information from the received repository's metadata to populate the containers_dict for display.  This method is called only
    from Galaxy (not the tool shed) when displaying repository dependencies for installed repositories and when displaying them for uninstalled
    repositories that are being reinstalled.
    """
    metadata = repository.metadata
    if metadata:
        # Handle proprietary datatypes.
        datatypes = metadata.get( 'datatypes', None )
        # Handle invalid tools.
        invalid_tools = metadata.get( 'invalid_tools', None )
        # Handle README files.
        if repository.has_readme_files:
            if reinstalling or repository.status not in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED,
                                                          trans.model.ToolShedRepository.installation_status.INSTALLED ]:
                # Since we're reinstalling, we need to send a request to the tool shed to get the README files.
                url = suc.url_join( tool_shed_url,
                                    'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % \
                                    ( repository.name, repository.owner, repository.installed_changeset_revision ) )
                raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
                readme_files_dict = json.from_json_string( raw_text )
            else:
                readme_files_dict = readme_util.build_readme_files_dict( repository.metadata, tool_path )
        else:
            readme_files_dict = None
        # Handle repository dependencies.
        installed_repository_dependencies, missing_repository_dependencies = \
            common_install_util.get_installed_and_missing_repository_dependencies( trans, repository )
        # Handle the current repository's tool dependencies.
        repository_tool_dependencies = metadata.get( 'tool_dependencies', None )
        repository_installed_tool_dependencies, repository_missing_tool_dependencies = \
            tool_dependency_util.get_installed_and_missing_tool_dependencies( trans, repository, repository_tool_dependencies )
        if reinstalling:
            installed_tool_dependencies, missing_tool_dependencies = \
                tool_dependency_util.populate_tool_dependencies_dicts( trans=trans,
                                                                       tool_shed_url=tool_shed_url,
                                                                       tool_path=tool_path,
                                                                       repository_installed_tool_dependencies=repository_installed_tool_dependencies,
                                                                       repository_missing_tool_dependencies=repository_missing_tool_dependencies,
                                                                       required_repo_info_dicts=required_repo_info_dicts )
        else:
            installed_tool_dependencies = repository_installed_tool_dependencies
            missing_tool_dependencies = repository_missing_tool_dependencies
        # Handle valid tools.
        valid_tools = metadata.get( 'tools', None )
        # Handle workflows.
        workflows = metadata.get( 'workflows', None )
        # Handle Data Managers
        valid_data_managers = None
        invalid_data_managers = None
        data_managers_errors = None
        if 'data_manager' in metadata:
            valid_data_managers = metadata['data_manager'].get( 'data_managers', None )
            invalid_data_managers = metadata['data_manager'].get( 'invalid_data_managers', None )
            data_managers_errors = metadata['data_manager'].get( 'messages', None )
        containers_dict = container_util.build_repository_containers_for_galaxy( trans=trans,
                                                                                 repository=repository,
                                                                                 datatypes=datatypes,
                                                                                 invalid_tools=invalid_tools,
                                                                                 missing_repository_dependencies=missing_repository_dependencies,
                                                                                 missing_tool_dependencies=missing_tool_dependencies,
                                                                                 readme_files_dict=readme_files_dict,
                                                                                 repository_dependencies=installed_repository_dependencies,
                                                                                 tool_dependencies=installed_tool_dependencies,
                                                                                 valid_tools=valid_tools,
                                                                                 workflows=workflows,
                                                                                 valid_data_managers=valid_data_managers,
                                                                                 invalid_data_managers=invalid_data_managers,
                                                                                 data_managers_errors=data_managers_errors,
                                                                                 new_install=False,
                                                                                 reinstalling=reinstalling )
    else:
        containers_dict = dict( datatypes=None,
                                invalid_tools=None,
                                readme_files_dict=None,
                                repository_dependencies=None,
                                tool_dependencies=None,
                                valid_tools=None,
                                workflows=None )
    return containers_dict

def reset_all_metadata_on_installed_repository( trans, id ):
    """Reset all metadata on a single tool shed repository installed into a Galaxy instance."""
    repository = suc.get_installed_tool_shed_repository( trans, id )
    tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
    repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, repository )
    tool_path, relative_install_dir = repository.get_tool_relative_path( trans.app )
    if relative_install_dir:
        original_metadata_dict = repository.metadata
        metadata_dict, invalid_file_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                     repository=repository,
                                                                                     changeset_revision=repository.changeset_revision,
                                                                                     repository_clone_url=repository_clone_url,
                                                                                     shed_config_dict = repository.get_shed_config_dict( trans.app ),
                                                                                     relative_install_dir=relative_install_dir,
                                                                                     repository_files_dir=None,
                                                                                     resetting_all_metadata_on_repository=False,
                                                                                     updating_installed_repository=False,
                                                                                     persist=False )
        repository.metadata = metadata_dict
        if metadata_dict != original_metadata_dict:
            suc.update_in_shed_tool_config( trans.app, repository )
            trans.sa_session.add( repository )
            trans.sa_session.flush()
            log.debug( 'Metadata has been reset on repository %s.' % repository.name )
        else:
            log.debug( 'Metadata did not need to be reset on repository %s.' % repository.name )
    else:
        log.debug( 'Error locating installation directory for repository %s.' % repository.name )
    return invalid_file_tups, metadata_dict

def reset_all_metadata_on_repository_in_tool_shed( trans, id ):
    """Reset all metadata on a single repository in a tool shed."""
    def reset_all_tool_versions( trans, id, repo ):
        """Reset tool version lineage for those changeset revisions that include valid tools."""
        changeset_revisions_that_contain_tools = []
        for changeset in repo.changelog:
            changeset_revision = str( repo.changectx( changeset ) )
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if metadata.get( 'tools', None ):
                        changeset_revisions_that_contain_tools.append( changeset_revision )
        # The list of changeset_revisions_that_contain_tools is now filtered to contain only those that are downloadable and contain tools.
        # If a repository includes tools, build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in each changeset revision.
        for index, changeset_revision in enumerate( changeset_revisions_that_contain_tools ):
            tool_versions_dict = {}
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
            metadata = repository_metadata.metadata
            tool_dicts = metadata[ 'tools' ]
            if index == 0:
                # The first changeset_revision is a special case because it will have no ancestor changeset_revisions in which to match tools.
                # The parent tool id for tools in the first changeset_revision will be the "old_id" in the tool config.
                for tool_dict in tool_dicts:
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = tool_dict[ 'id' ]
            else:
                for tool_dict in tool_dicts:
                    parent_id = get_parent_id( trans,
                                               id,
                                               tool_dict[ 'id' ],
                                               tool_dict[ 'version' ],
                                               tool_dict[ 'guid' ],
                                               changeset_revisions_that_contain_tools[ 0:index ] )
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
            if tool_versions_dict:
                repository_metadata.tool_versions = tool_versions_dict
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
    repository = suc.get_repository_in_tool_shed( trans, id )
    log.debug( "Resetting all metadata on repository: %s" % repository.name )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( suc.get_configured_ui(), repo_dir )
    repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( trans, repository )
    # The list of changeset_revisions refers to repository_metadata records that have been created or updated.  When the following loop
    # completes, we'll delete all repository_metadata records for this repository that do not have a changeset_revision value in this list.
    changeset_revisions = []
    # When a new repository_metadata record is created, it always uses the values of metadata_changeset_revision and metadata_dict.
    metadata_changeset_revision = None
    metadata_dict = None
    ancestor_changeset_revision = None
    ancestor_metadata_dict = None
    invalid_file_tups = []
    home_dir = os.getcwd()
    for changeset in repo.changelog:
        work_dir = tempfile.mkdtemp()
        current_changeset_revision = str( repo.changectx( changeset ) )
        ctx = repo.changectx( changeset )
        log.debug( "Cloning repository changeset revision: %s", str( ctx.rev() ) )
        cloned_ok, error_message = suc.clone_repository( repository_clone_url, work_dir, str( ctx.rev() ) )
        if cloned_ok:
            log.debug( "Generating metadata for changset revision: %s", str( ctx.rev() ) )
            current_metadata_dict, invalid_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                            repository=repository,
                                                                                            changeset_revision=current_changeset_revision,
                                                                                            repository_clone_url=repository_clone_url,
                                                                                            relative_install_dir=repo_dir,
                                                                                            repository_files_dir=work_dir,
                                                                                            resetting_all_metadata_on_repository=True,
                                                                                            updating_installed_repository=False,
                                                                                            persist=False )
            # We'll only display error messages for the repository tip (it may be better to display error messages for each installable changeset revision).
            if current_changeset_revision == repository.tip( trans.app ):
                invalid_file_tups.extend( invalid_tups )
            if current_metadata_dict:
                if metadata_changeset_revision is None and metadata_dict is None:
                    # We're at the first change set in the change log.
                    metadata_changeset_revision = current_changeset_revision
                    metadata_dict = current_metadata_dict
                if ancestor_changeset_revision:
                    # Compare metadata from ancestor and current.  The value of comparison will be one of:
                    # 'no metadata' - no metadata for either ancestor or current, so continue from current
                    # 'equal' - ancestor metadata is equivalent to current metadata, so continue from current
                    # 'subset' - ancestor metadata is a subset of current metadata, so continue from current
                    # 'not equal and not subset' - ancestor metadata is neither equal to nor a subset of current metadata, so persist ancestor metadata.
                    comparison = compare_changeset_revisions( ancestor_changeset_revision,
                                                              ancestor_metadata_dict,
                                                              current_changeset_revision,
                                                              current_metadata_dict )
                    if comparison in [ 'no metadata', 'equal', 'subset' ]:
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                    elif comparison == 'not equal and not subset':
                        metadata_changeset_revision = ancestor_changeset_revision
                        metadata_dict = ancestor_metadata_dict
                        repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                        changeset_revisions.append( metadata_changeset_revision )
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                else:
                    # We're at the beginning of the change log.
                    ancestor_changeset_revision = current_changeset_revision
                    ancestor_metadata_dict = current_metadata_dict
                if not ctx.children():
                    metadata_changeset_revision = current_changeset_revision
                    metadata_dict = current_metadata_dict
                    # We're at the end of the change log.
                    repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                    changeset_revisions.append( metadata_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
            elif ancestor_metadata_dict:
                # We reach here only if current_metadata_dict is empty and ancestor_metadata_dict is not.
                if not ctx.children():
                    # We're at the end of the change log.
                    repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                    changeset_revisions.append( metadata_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
        suc.remove_dir( work_dir )
    # Delete all repository_metadata records for this repository that do not have a changeset_revision value in changeset_revisions.
    clean_repository_metadata( trans, id, changeset_revisions )
    # Set tool version information for all downloadable changeset revisions.  Get the list of changeset revisions from the changelog.
    reset_all_tool_versions( trans, id, repo )
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    tool_util.reset_tool_data_tables( trans.app )
    return invalid_file_tups, metadata_dict

def reset_metadata_on_selected_repositories( trans, **kwd ):
    """
    Inspect the repository changelog to reset metadata for all appropriate changeset revisions.  This method is called from both Galaxy and the
    Tool Shed.
    """
    repository_ids = util.listify( kwd.get( 'repository_ids', None ) )
    message = ''
    status = 'done'
    if repository_ids:
        successful_count = 0
        unsuccessful_count = 0
        for repository_id in repository_ids:
            try:
                if trans.webapp.name == 'tool_shed':
                    # We're in the tool shed.
                    repository = suc.get_repository_in_tool_shed( trans, repository_id )
                    invalid_file_tups, metadata_dict = reset_all_metadata_on_repository_in_tool_shed( trans, repository_id )
                else:
                    # We're in Galaxy.
                    repository = suc.get_installed_tool_shed_repository( trans, repository_id )
                    invalid_file_tups, metadata_dict = reset_all_metadata_on_installed_repository( trans, repository_id )
                if invalid_file_tups:
                    message = tool_util.generate_message_for_invalid_tools( trans, invalid_file_tups, repository, None, as_html=False )
                    log.debug( message )
                    unsuccessful_count += 1
                else:
                    log.debug( "Successfully reset metadata on repository %s" % repository.name )
                    successful_count += 1
            except Exception, e:
                log.debug( "Error attempting to reset metadata on repository: %s" % str( e ) )
                unsuccessful_count += 1
        message = "Successfully reset metadata on %d %s.  " % ( successful_count, inflector.cond_plural( successful_count, "repository" ) )
        if unsuccessful_count:
            message += "Error setting metadata on %d %s - see the paster log for details.  " % ( unsuccessful_count,
                                                                                                 inflector.cond_plural( unsuccessful_count, "repository" ) )
    else:
        message = 'Select at least one repository to on which to reset all metadata.'
        status = 'error'
    return message, status

def set_add_to_tool_panel_attribute_for_tool( tool, guid, datatypes ):
    """
    Determine if a tool should be loaded into the Galaxy tool panel.  Examples of valid tools that should not be displayed in the tool panel are datatypes
    converters and DataManager tools.
    """
    if hasattr( tool, 'tool_type' ):
        if tool.tool_type in [ 'manage_data' ]:
            # We have a DataManager tool.
            return False
    if datatypes:
        for datatype_dict in datatypes:
            converters = datatype_dict.get( 'converters', None )
            # [{"converters": 
            #    [{"target_datatype": "gff", 
            #      "tool_config": "bed_to_gff_converter.xml", 
            #      "guid": "localhost:9009/repos/test/bed_to_gff_converter/CONVERTER_bed_to_gff_0/2.0.0"}], 
            #   "display_in_upload": "true", 
            #   "dtype": "galaxy.datatypes.interval:Bed", 
            #   "extension": "bed"}]
            if converters:
                for converter_dict in converters:
                    converter_guid = converter_dict.get( 'guid', None )
                    if converter_guid:
                        if converter_guid == guid:
                            # We have a datatypes converter.
                            return False
    return True

def set_repository_metadata( trans, repository, content_alert_str='', **kwd ):
    """
    Set metadata using the repository's current disk files, returning specific error messages (if any) to alert the repository owner that the changeset
    has problems.
    """
    message = ''
    status = 'done'
    encoded_id = trans.security.encode_id( repository.id )
    repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( trans, repository )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( suc.get_configured_ui(), repo_dir )
    metadata_dict, invalid_file_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                 repository=repository,
                                                                                 changeset_revision=repository.tip( trans.app ),
                                                                                 repository_clone_url=repository_clone_url,
                                                                                 relative_install_dir=repo_dir,
                                                                                 repository_files_dir=None,
                                                                                 resetting_all_metadata_on_repository=False,
                                                                                 updating_installed_repository=False,
                                                                                 persist=False )
    if metadata_dict:
        repository_metadata = None
        if new_metadata_required_for_utilities( trans, repository, metadata_dict ):
            # Create a new repository_metadata table row.
            repository_metadata = create_or_update_repository_metadata( trans, encoded_id, repository, repository.tip( trans.app ), metadata_dict )
            # If this is the first record stored for this repository, see if we need to send any email alerts.
            if len( repository.downloadable_revisions ) == 1:
                suc.handle_email_alerts( trans, repository, content_alert_str='', new_repo_alert=True, admin_only=False )
        else:
            # Update the latest stored repository metadata with the contents and attributes of metadata_dict.
            repository_metadata = get_latest_repository_metadata( trans, repository.id )
            if repository_metadata:
                downloadable = is_downloadable( metadata_dict )
                # Update the last saved repository_metadata table row.
                repository_metadata.changeset_revision = repository.tip( trans.app )
                repository_metadata.metadata = metadata_dict
                repository_metadata.downloadable = downloadable
                if 'datatypes' in metadata_dict:
                    repository_metadata.includes_datatypes = True
                else:
                    repository_metadata.includes_datatypes = False
                if 'repository_dependencies' in metadata_dict:
                    repository_metadata.has_repository_dependencies = True
                else:
                    repository_metadata.has_repository_dependencies = False
                if 'tool_dependencies' in metadata_dict:
                    repository_metadata.includes_tool_dependencies = True
                else:
                    repository_metadata.includes_tool_dependencies = False
                if 'tools' in metadata_dict:
                    repository_metadata.includes_tools = True
                else:
                    repository_metadata.includes_tools = False
                if 'workflows' in metadata_dict:
                    repository_metadata.includes_workflows = True
                else:
                    repository_metadata.includes_workflows = False
                repository_metadata.do_not_test = False
                repository_metadata.time_last_tested = None
                repository_metadata.tools_functionally_correct = False
                repository_metadata.missing_test_components = False
                repository_metadata.tool_test_results = None
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
            else:
                # There are no metadata records associated with the repository.
                repository_metadata = create_or_update_repository_metadata( trans, encoded_id, repository, repository.tip( trans.app ), metadata_dict )
        if 'tools' in metadata_dict and repository_metadata and status != 'error':
            # Set tool versions on the new downloadable change set.  The order of the list of changesets is critical, so we use the repo's changelog.
            changeset_revisions = []
            for changeset in repo.changelog:
                changeset_revision = str( repo.changectx( changeset ) )
                if suc.get_repository_metadata_by_changeset_revision( trans, encoded_id, changeset_revision ):
                    changeset_revisions.append( changeset_revision )
            add_tool_versions( trans, encoded_id, repository_metadata, changeset_revisions )
    elif len( repo ) == 1 and not invalid_file_tups:
        message = "Revision '%s' includes no tools, datatypes or exported workflows for which metadata can " % str( repository.tip( trans.app ) )
        message += "be defined so this revision cannot be automatically installed into a local Galaxy instance."
        status = "error"
    if invalid_file_tups:
        message = tool_util.generate_message_for_invalid_tools( trans, invalid_file_tups, repository, metadata_dict )
        status = 'error'
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    tool_util.reset_tool_data_tables( trans.app )
    return message, status

def set_repository_metadata_due_to_new_tip( trans, repository, content_alert_str=None, **kwd ):
    """Set metadata on the repository tip in the tool shed - this method is not called from Galaxy."""
    error_message, status = set_repository_metadata( trans, repository, content_alert_str=content_alert_str, **kwd )
    if error_message:
        # FIXME: This probably should not redirect since this method is called from the upload controller as well as the repository controller.
        # If there is an error, display it.
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=trans.security.encode_id( repository.id ),
                                                          message=error_message,
                                                          status='error' ) )

def tool_dependency_is_orphan( type, name, version, tools ):
    """
    Determine if the combination of the received type, name and version is defined in the <requirement> tag for at least one tool in the received list of tools.
    If not, the tool dependency defined by the combination is considered an orphan in it's repository in the tool shed.
    """
    if tools:
        if type == 'package':
            if name and version:
                for tool_dict in tools:
                    requirements = tool_dict.get( 'requirements', [] )
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get( 'name', None )
                        req_version = requirement_dict.get( 'version', None )
                        req_type = requirement_dict.get( 'type', None )
                        if req_name == name and req_version == version and req_type == type:
                            return False
        elif type == 'set_environment':
            if name:
                for tool_dict in tools:
                    requirements = tool_dict.get( 'requirements', [] )
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get( 'name', None )
                        req_type = requirement_dict.get( 'type', None )
                        if req_name == name and req_type == type:
                            return False
    return True

def update_existing_tool_dependency( app, repository, original_dependency_dict, new_dependencies_dict ):
    """
    Update an exsiting tool dependency whose definition was updated in a change set pulled by a Galaxy administrator when getting updates 
    to an installed tool shed repository.  The original_dependency_dict is a single tool dependency definition, an example of which is::

        {"name": "bwa", 
         "readme": "\\nCompiling BWA requires zlib and libpthread to be present on your system.\\n        ", 
         "type": "package", 
         "version": "0.6.2"}

    The new_dependencies_dict is the dictionary generated by the metadata_util.generate_tool_dependency_metadata method.
    """
    new_tool_dependency = None
    original_name = original_dependency_dict[ 'name' ]
    original_type = original_dependency_dict[ 'type' ]
    original_version = original_dependency_dict[ 'version' ]
    # Locate the appropriate tool_dependency associated with the repository.
    tool_dependency = None
    for tool_dependency in repository.tool_dependencies:
        if tool_dependency.name == original_name and tool_dependency.type == original_type and tool_dependency.version == original_version:
            break
    if tool_dependency and tool_dependency.can_update:
        dependency_install_dir = tool_dependency.installation_directory( app )
        removed_from_disk, error_message = tool_dependency_util.remove_tool_dependency_installation_directory( dependency_install_dir )
        if removed_from_disk:
            sa_session = app.model.context.current
            new_dependency_name = None
            new_dependency_type = None
            new_dependency_version = None
            for new_dependency_key, new_dependency_val_dict in new_dependencies_dict.items():
                # Match on name only, hopefully this will be enough!
                if original_name == new_dependency_val_dict[ 'name' ]:
                    new_dependency_name = new_dependency_val_dict[ 'name' ]
                    new_dependency_type = new_dependency_val_dict[ 'type' ]
                    new_dependency_version = new_dependency_val_dict[ 'version' ]
                    break
            if new_dependency_name and new_dependency_type and new_dependency_version:
                # Update all attributes of the tool_dependency record in the database.
                log.debug( "Updating tool dependency '%s' with type '%s' and version '%s' to have new type '%s' and version '%s'." % \
                           ( str( tool_dependency.name ), str( tool_dependency.type ), str( tool_dependency.version ), str( new_dependency_type ), str( new_dependency_version ) ) )
                tool_dependency.type = new_dependency_type
                tool_dependency.version = new_dependency_version
                tool_dependency.status = app.model.ToolDependency.installation_status.UNINSTALLED
                tool_dependency.error_message = None
                sa_session.add( tool_dependency )
                sa_session.flush()
                new_tool_dependency = tool_dependency
            else:
                # We have no new tool dependency definition based on a matching dependency name, so remove the existing tool dependency record from the database.
                log.debug( "Deleting tool dependency with name '%s', type '%s' and version '%s' from the database since it is no longer defined." % \
                           ( str( tool_dependency.name ), str( tool_dependency.type ), str( tool_dependency.version ) ) )
                sa_session.delete( tool_dependency )
                sa_session.flush()
    return new_tool_dependency

def update_repository_dependencies_metadata( metadata, repository_dependency_tups, is_valid, description ):
    if is_valid:
        repository_dependencies_dict = metadata.get( 'repository_dependencies', None )
    else:
        repository_dependencies_dict = metadata.get( 'invalid_repository_dependencies', None )
    for repository_dependency_tup in repository_dependency_tups:
        if is_valid:
            tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tup
        else:
            tool_shed, name, owner, changeset_revision, prior_installation_required, error_message = repository_dependency_tup
        prior_installation_required = util.asbool( str( prior_installation_required ) )
        if repository_dependencies_dict:
            repository_dependencies = repository_dependencies_dict.get( 'repository_dependencies', [] )
            for repository_dependency_tup in repository_dependency_tups:
                if repository_dependency_tup not in repository_dependencies:
                    repository_dependencies.append( repository_dependency_tup )
            repository_dependencies_dict[ 'repository_dependencies' ] = repository_dependencies
        else:
            repository_dependencies_dict = dict( description=description,
                                                 repository_dependencies=repository_dependency_tups )
    if repository_dependencies_dict:
        if is_valid:
            metadata[ 'repository_dependencies' ] = repository_dependencies_dict
        else:
            metadata[ 'invalid_repository_dependencies' ] = repository_dependencies_dict
    return metadata
