"""
Manage automatic installation of tools configured in the xxx.xml files in ~/scripts/migrate_tools (e.g., 0002_tools.xml).
All of the tools were at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool shed.
"""
import logging
import os
import shutil
import tempfile
import threading

from galaxy import util
from galaxy.tools.toolbox import ToolSection
from galaxy.tools.toolbox.parser import ensure_tool_conf_item
from galaxy.util.odict import odict
from tool_shed.galaxy_install import install_manager
from tool_shed.galaxy_install.datatypes import custom_datatype_manager
from tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import InstalledRepositoryMetadataManager
from tool_shed.galaxy_install.tools import tool_panel_manager
from tool_shed.tools import data_table_manager
from tool_shed.util import (
    basic_util,
    common_util,
    hg_util,
    repository_util,
    shed_util_common as suc,
    tool_dependency_util,
    tool_util,
    xml_util
)

log = logging.getLogger(__name__)


class ToolMigrationManager(object):

    def __init__(self, app, latest_migration_script_number, tool_shed_install_config, migrated_tools_config,
                 install_dependencies):
        """
        Check tool settings in tool_shed_install_config and install all repositories
        that are not already installed.  The tool panel configuration file is the received
        migrated_tools_config, which is the reserved file named migrated_tools_conf.xml.
        """
        self.app = app
        self.toolbox = self.app.toolbox
        self.migrated_tools_config = migrated_tools_config
        # Initialize the ToolPanelManager.
        self.tpm = tool_panel_manager.ToolPanelManager(self.app)
        # If install_dependencies is True but tool_dependency_dir is not set, do not attempt
        # to install but print informative error message.
        if install_dependencies and app.config.tool_dependency_dir is None:
            message = 'You are attempting to install tool dependencies but do not have a value '
            message += 'for "tool_dependency_dir" set in your galaxy.ini file.  Set this '
            message += 'location value to the path where you want tool dependencies installed and '
            message += 'rerun the migration script.'
            raise Exception(message)
        # Get the local non-shed related tool panel configs (there can be more than one, and the
        # default name is tool_conf.xml).
        self.proprietary_tool_confs = self.non_shed_tool_panel_configs
        self.proprietary_tool_panel_elems = self.get_proprietary_tool_panel_elems(latest_migration_script_number)
        # Set the location where the repositories will be installed by retrieving the tool_path
        # setting from migrated_tools_config.
        tree, error_message = xml_util.parse_xml(migrated_tools_config)
        if tree is None:
            log.error(error_message)
        else:
            root = tree.getroot()
            self.tool_path = root.get('tool_path')
            log.debug("Repositories will be installed into configured tool_path location ", str(self.tool_path))
            # Parse tool_shed_install_config to check each of the tools.
            self.tool_shed_install_config = tool_shed_install_config
            tree, error_message = xml_util.parse_xml(tool_shed_install_config)
            if tree is None:
                log.error(error_message)
            else:
                root = tree.getroot()
                defined_tool_shed_url = root.get('name')
                self.tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(self.app, defined_tool_shed_url)
                self.tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url(self.tool_shed_url)
                self.repository_owner = common_util.REPOSITORY_OWNER
                self.shed_config_dict = self.tpm.get_shed_tool_conf_dict(self.migrated_tools_config)
                # Since tool migration scripts can be executed any number of times, we need to
                # make sure the appropriate tools are defined in tool_conf.xml.  If no tools
                # associated with the migration stage are defined, no repositories will be installed
                # on disk.  The default behavior is that the tool shed is down.
                tool_shed_accessible = False
                tool_panel_configs = common_util.get_non_shed_tool_panel_configs(app)
                if tool_panel_configs:
                    # The missing_tool_configs_dict contents are something like:
                    # {'emboss_antigenic.xml': [('emboss', '5.0.0', 'package', '\nreadme blah blah blah\n')]}
                    tool_shed_accessible, missing_tool_configs_dict = \
                        common_util.check_for_missing_tools(app,
                                                            tool_panel_configs,
                                                            latest_migration_script_number)
                else:
                    # It doesn't matter if the tool shed is accessible since there are no migrated
                    # tools defined in the local Galaxy instance, but we have to set the value of
                    # tool_shed_accessible to True so that the value of migrate_tools.version can
                    # be correctly set in the database.
                    tool_shed_accessible = True
                    missing_tool_configs_dict = odict()
                if tool_shed_accessible:
                    if len(self.proprietary_tool_confs) == 1:
                        plural = ''
                        file_names = self.proprietary_tool_confs[0]
                    else:
                        plural = 's'
                        file_names = ', '.join(self.proprietary_tool_confs)
                    if missing_tool_configs_dict:
                        for proprietary_tool_conf in self.proprietary_tool_confs:
                            # Create a backup of the tool configuration in the un-migrated state.
                            shutil.copy(proprietary_tool_conf, '%s-pre-stage-%04d' % (proprietary_tool_conf,
                                                                                      latest_migration_script_number))
                        for repository_elem in root:
                            # Make sure we have a valid repository tag.
                            if self.__is_valid_repository_tag(repository_elem):
                                # Get all repository dependencies for the repository defined by the
                                # current repository_elem.  Repository dependency definitions contained
                                # in tool shed repositories with migrated tools must never define a
                                # relationship to a repository dependency that contains a tool.  The
                                # repository dependency can only contain items that are not loaded into
                                # the Galaxy tool panel (e.g., tool dependency definitions, custom datatypes,
                                # etc).  This restriction must be followed down the entire dependency hierarchy.
                                name = repository_elem.get('name')
                                changeset_revision = repository_elem.get('changeset_revision')
                                tool_shed_accessible, repository_dependencies_dict = \
                                    common_util.get_repository_dependencies(app,
                                                                            self.tool_shed_url,
                                                                            name,
                                                                            self.repository_owner,
                                                                            changeset_revision)
                                # Make sure all repository dependency records exist (as tool_shed_repository
                                # table rows) in the Galaxy database.
                                created_tool_shed_repositories = \
                                    self.create_or_update_tool_shed_repository_records(name,
                                                                                       changeset_revision,
                                                                                       repository_dependencies_dict)
                                # Order the repositories for proper installation.  This process is similar to the
                                # process used when installing tool shed repositories, but does not handle managing
                                # tool panel sections and other components since repository dependency definitions
                                # contained in tool shed repositories with migrated tools must never define a relationship
                                # to a repository dependency that contains a tool.
                                ordered_tool_shed_repositories = \
                                    self.order_repositories_for_installation(created_tool_shed_repositories,
                                                                             repository_dependencies_dict)

                                for tool_shed_repository in ordered_tool_shed_repositories:
                                    is_repository_dependency = self.__is_repository_dependency(name,
                                                                                               changeset_revision,
                                                                                               tool_shed_repository)
                                    self.install_repository(repository_elem,
                                                            tool_shed_repository,
                                                            install_dependencies,
                                                            is_repository_dependency=is_repository_dependency)
                    else:
                        message = "\nNo tools associated with migration stage %s are defined in your " % \
                            str(latest_migration_script_number)
                        message += "file%s named %s,\nso no repositories will be installed on disk.\n" % \
                            (plural, file_names)
                        log.info(message)
                else:
                    message = "\nThe main Galaxy tool shed is not currently available, so skipped migration stage %s.\n" % \
                        str(latest_migration_script_number)
                    message += "Try again later.\n"
                    log.error(message)

    def create_or_update_tool_shed_repository_record(self, name, owner, changeset_revision, description=None):

        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<installed changeset revision>
        relative_clone_dir = os.path.join(self.tool_shed, 'repos', owner, name, changeset_revision)
        clone_dir = os.path.join(self.tool_path, relative_clone_dir)
        if not self.__iscloned(clone_dir):
            repository_clone_url = os.path.join(self.tool_shed_url, 'repos', owner, name)
            ctx_rev = suc.get_ctx_rev(self.app, self.tool_shed_url, name, owner, changeset_revision)
            tool_shed_repository = repository_util.create_or_update_tool_shed_repository(app=self.app,
                                                                                         name=name,
                                                                                         description=description,
                                                                                         installed_changeset_revision=changeset_revision,
                                                                                         ctx_rev=ctx_rev,
                                                                                         repository_clone_url=repository_clone_url,
                                                                                         metadata_dict={},
                                                                                         status=self.app.install_model.ToolShedRepository.installation_status.NEW,
                                                                                         current_changeset_revision=None,
                                                                                         owner=self.repository_owner,
                                                                                         dist_to_shed=True)
            return tool_shed_repository
        return None

    def create_or_update_tool_shed_repository_records(self, name, changeset_revision, repository_dependencies_dict):
        """
        Make sure the repository defined by name and changeset_revision and all of its repository dependencies have
        associated tool_shed_repository table rows in the Galaxy database.
        """
        created_tool_shed_repositories = []
        description = repository_dependencies_dict.get('description', None)
        tool_shed_repository = self.create_or_update_tool_shed_repository_record(name,
                                                                                 self.repository_owner,
                                                                                 changeset_revision,
                                                                                 description=description)
        if tool_shed_repository:
            created_tool_shed_repositories.append(tool_shed_repository)
        for rd_key, rd_tups in repository_dependencies_dict.items():
            if rd_key in ['root_key', 'description']:
                continue
            for rd_tup in rd_tups:
                parsed_rd_tup = common_util.parse_repository_dependency_tuple(rd_tup)
                rd_tool_shed, rd_name, rd_owner, rd_changeset_revision = parsed_rd_tup[0:4]
                # TODO: Make sure the repository description is applied to the new repository record during installation.
                tool_shed_repository = self.create_or_update_tool_shed_repository_record(rd_name,
                                                                                         rd_owner,
                                                                                         rd_changeset_revision,
                                                                                         description=None)
                if tool_shed_repository:
                    created_tool_shed_repositories.append(tool_shed_repository)
        return created_tool_shed_repositories

    def filter_and_persist_proprietary_tool_panel_configs(self, tool_configs_to_filter):
        """Eliminate all entries in all non-shed-related tool panel configs for all tool config file names in the received tool_configs_to_filter."""
        for proprietary_tool_conf in self.proprietary_tool_confs:
            persist_required = False
            tree, error_message = xml_util.parse_xml(proprietary_tool_conf)
            if tree:
                root = tree.getroot()
                for elem in root:
                    if elem.tag == 'tool':
                        # Tools outside of sections.
                        file_path = elem.get('file', None)
                        if file_path:
                            if file_path in tool_configs_to_filter:
                                root.remove(elem)
                                persist_required = True
                    elif elem.tag == 'section':
                        # Tools contained in a section.
                        for section_elem in elem:
                            if section_elem.tag == 'tool':
                                file_path = section_elem.get('file', None)
                                if file_path:
                                    if file_path in tool_configs_to_filter:
                                        elem.remove(section_elem)
                                        persist_required = True
            if persist_required:
                fh = tempfile.NamedTemporaryFile('wb', prefix="tmp-toolshed-fapptpc")
                tmp_filename = fh.name
                fh.close()
                fh = open(tmp_filename, 'wb')
                tree.write(tmp_filename, encoding='utf-8', xml_declaration=True)
                fh.close()
                shutil.move(tmp_filename, os.path.abspath(proprietary_tool_conf))
                os.chmod(proprietary_tool_conf, 0o644)

    def get_containing_tool_sections(self, tool_config):
        """
        If tool_config is defined somewhere in self.proprietary_tool_panel_elems, return True and a list of ToolSections in which the
        tool is displayed.  If the tool is displayed outside of any sections, None is appended to the list.
        """
        tool_sections = []
        is_displayed = False
        for proprietary_tool_panel_elem in self.proprietary_tool_panel_elems:
            if proprietary_tool_panel_elem.tag == 'tool':
                # The proprietary_tool_panel_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                proprietary_tool_config = proprietary_tool_panel_elem.get('file')
                if tool_config == proprietary_tool_config:
                    # The tool is loaded outside of any sections.
                    tool_sections.append(None)
                    if not is_displayed:
                        is_displayed = True
            if proprietary_tool_panel_elem.tag == 'section':
                # The proprietary_tool_panel_elem looks something like <section name="EMBOSS" id="EMBOSSLite">.
                for section_elem in proprietary_tool_panel_elem:
                    if section_elem.tag == 'tool':
                        # The section_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                        proprietary_tool_config = section_elem.get('file')
                        if tool_config == proprietary_tool_config:
                            # The tool is loaded inside of the section_elem.
                            tool_sections.append(ToolSection(ensure_tool_conf_item(proprietary_tool_panel_elem)))
                            if not is_displayed:
                                is_displayed = True
        return is_displayed, tool_sections

    def get_guid(self, repository_clone_url, relative_install_dir, tool_config):
        if self.shed_config_dict.get('tool_path'):
            relative_install_dir = os.path.join(self.shed_config_dict['tool_path'], relative_install_dir)
        tool_config_filename = basic_util.strip_path(tool_config)
        for root, dirs, files in os.walk(relative_install_dir):
            if root.find('.hg') < 0 and root.find('hgrc') < 0:
                if '.hg' in dirs:
                    dirs.remove('.hg')
                for name in files:
                    filename = basic_util.strip_path(name)
                    if filename == tool_config_filename:
                        full_path = str(os.path.abspath(os.path.join(root, name)))
                        tool = self.toolbox.load_tool(full_path, use_cached=False)
                        return suc.generate_tool_guid(repository_clone_url, tool)
        # Not quite sure what should happen here, throw an exception or what?
        return None

    def get_prior_install_required_dict(self, tool_shed_repositories, repository_dependencies_dict):
        """
        Return a dictionary whose keys are the received tsr_ids and whose values are a list of tsr_ids, each of which is contained in the received
        list of tsr_ids and whose associated repository must be installed prior to the repository associated with the tsr_id key.
        """
        # Initialize the dictionary.
        prior_install_required_dict = {}
        tsr_ids = [tool_shed_repository.id for tool_shed_repository in tool_shed_repositories]
        for tsr_id in tsr_ids:
            prior_install_required_dict[tsr_id] = []
        # Inspect the repository dependencies about to be installed and populate the dictionary.
        for rd_key, rd_tups in repository_dependencies_dict.items():
            if rd_key in ['root_key', 'description']:
                continue
            for rd_tup in rd_tups:
                prior_install_ids = []
                tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                    common_util.parse_repository_dependency_tuple(rd_tup)
                if util.asbool(prior_installation_required):
                    for tsr in tool_shed_repositories:
                        if tsr.name == name and tsr.owner == owner and tsr.changeset_revision == changeset_revision:
                            prior_install_ids.append(tsr.id)
                        prior_install_required_dict[tsr.id] = prior_install_ids
        return prior_install_required_dict

    def get_proprietary_tool_panel_elems(self, latest_tool_migration_script_number):
        """
        Parse each config in self.proprietary_tool_confs (the default is tool_conf.xml) and generate a list of Elements that are
        either ToolSection elements or Tool elements.  These will be used to generate new entries in the migrated_tools_conf.xml
        file for the installed tools.
        """
        tools_xml_file_path = os.path.abspath(os.path.join('scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number))
        # Parse the XML and load the file attributes for later checking against the integrated elements from self.proprietary_tool_confs.
        migrated_tool_configs = []
        tree, error_message = xml_util.parse_xml(tools_xml_file_path)
        if tree is None:
            return []
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'repository':
                for tool_elem in elem:
                    migrated_tool_configs.append(tool_elem.get('file'))
        # Parse each file in self.proprietary_tool_confs and generate the integrated list of tool panel Elements that contain them.
        tool_panel_elems = []
        for proprietary_tool_conf in self.proprietary_tool_confs:
            tree, error_message = xml_util.parse_xml(proprietary_tool_conf)
            if tree is None:
                return []
            root = tree.getroot()
            for elem in root:
                if elem.tag == 'tool':
                    # Tools outside of sections.
                    file_path = elem.get('file', None)
                    if file_path:
                        if file_path in migrated_tool_configs:
                            if elem not in tool_panel_elems:
                                tool_panel_elems.append(elem)
                elif elem.tag == 'section':
                    # Tools contained in a section.
                    for section_elem in elem:
                        if section_elem.tag == 'tool':
                            file_path = section_elem.get('file', None)
                            if file_path:
                                if file_path in migrated_tool_configs:
                                    # Append the section, not the tool.
                                    if elem not in tool_panel_elems:
                                        tool_panel_elems.append(elem)
        return tool_panel_elems

    def handle_repository_contents(self, tool_shed_repository, repository_clone_url, relative_install_dir, repository_elem,
                                   install_dependencies, is_repository_dependency=False):
        """
        Generate the metadata for the installed tool shed repository, among other things.  If the installed tool_shed_repository
        contains tools that are loaded into the Galaxy tool panel, this method will automatically eliminate all entries for each
        of the tools defined in the received repository_elem from all non-shed-related tool panel configuration files since the
        entries are automatically added to the reserved migrated_tools_conf.xml file as part of the migration process.
        """
        tool_configs_to_filter = []
        tool_panel_dict_for_display = odict()
        if self.tool_path:
            repo_install_dir = os.path.join(self.tool_path, relative_install_dir)
        else:
            repo_install_dir = relative_install_dir
        if not is_repository_dependency:
            for tool_elem in repository_elem:
                # The tool_elem looks something like this:
                # <tool id="EMBOSS: antigenic1" version="5.0.0" file="emboss_antigenic.xml" />
                tool_config = tool_elem.get('file')
                guid = self.get_guid(repository_clone_url, relative_install_dir, tool_config)
                # See if tool_config is defined inside of a section in self.proprietary_tool_panel_elems.
                is_displayed, tool_sections = self.get_containing_tool_sections(tool_config)
                if is_displayed:
                    tool_panel_dict_for_tool_config = \
                        self.tpm.generate_tool_panel_dict_for_tool_config(guid,
                                                                          tool_config,
                                                                          tool_sections=tool_sections)
                    # The tool-panel_dict has the following structure.
                    # {<Tool guid> : [{ tool_config : <tool_config_file>,
                    #                   id: <ToolSection id>,
                    #                   version : <ToolSection version>,
                    #                   name : <TooSection name>}]}
                    for k, v in tool_panel_dict_for_tool_config.items():
                        tool_panel_dict_for_display[k] = v
                        for tool_panel_dict in v:
                            # Keep track of tool config file names associated with entries that have been made to the
                            # migrated_tools_conf.xml file so they can be eliminated from all non-shed-related tool panel configs.
                            if tool_config not in tool_configs_to_filter:
                                tool_configs_to_filter.append(tool_config)
                else:
                    log.error('The tool "%s" (%s) has not been enabled because it is not defined in a proprietary tool config (%s).'
                        % (guid, tool_config, ", ".join(self.proprietary_tool_confs or [])))
            if tool_configs_to_filter:
                lock = threading.Lock()
                lock.acquire(True)
                try:
                    self.filter_and_persist_proprietary_tool_panel_configs(tool_configs_to_filter)
                except Exception:
                    log.exception("Exception attempting to filter and persist non-shed-related tool panel configs")
                finally:
                    lock.release()
        irmm = InstalledRepositoryMetadataManager(app=self.app,
                                                  tpm=self.tpm,
                                                  repository=tool_shed_repository,
                                                  changeset_revision=tool_shed_repository.changeset_revision,
                                                  repository_clone_url=repository_clone_url,
                                                  shed_config_dict=self.shed_config_dict,
                                                  relative_install_dir=relative_install_dir,
                                                  repository_files_dir=None,
                                                  resetting_all_metadata_on_repository=False,
                                                  updating_installed_repository=False,
                                                  persist=True)
        irmm.generate_metadata_for_changeset_revision()
        irmm_metadata_dict = irmm.get_metadata_dict()
        tool_shed_repository.metadata = irmm_metadata_dict
        self.app.install_model.context.add(tool_shed_repository)
        self.app.install_model.context.flush()
        has_tool_dependencies = self.__has_tool_dependencies(irmm_metadata_dict)
        if has_tool_dependencies:
            # All tool_dependency objects must be created before the tools are processed even if no
            # tool dependencies will be installed.
            tool_dependencies = tool_dependency_util.create_tool_dependency_objects(self.app,
                                                                                    tool_shed_repository,
                                                                                    relative_install_dir,
                                                                                    set_status=True)
        else:
            tool_dependencies = None
        if 'tools' in irmm_metadata_dict:
            tdtm = data_table_manager.ToolDataTableManager(self.app)
            sample_files = irmm_metadata_dict.get('sample_files', [])
            sample_files = [str(s) for s in sample_files]
            tool_index_sample_files = tdtm.get_tool_index_sample_files(sample_files)
            tool_util.copy_sample_files(self.app, tool_index_sample_files, tool_path=self.tool_path)
            sample_files_copied = [s for s in tool_index_sample_files]
            repository_tools_tups = irmm.get_repository_tools_tups()
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically
                # generated select lists.
                repository_tools_tups = tdtm.handle_missing_data_table_entry(relative_install_dir,
                                                                             self.tool_path,
                                                                             repository_tools_tups)
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups, sample_files_copied = tool_util.handle_missing_index_file(self.app,
                                                                                                 self.tool_path,
                                                                                                 sample_files,
                                                                                                 repository_tools_tups,
                                                                                                 sample_files_copied)
                # Copy remaining sample files included in the repository to the ~/tool-data
                # directory of the local Galaxy instance.
                tool_util.copy_sample_files(self.app,
                                            sample_files,
                                            tool_path=self.tool_path,
                                            sample_files_copied=sample_files_copied)
                if not is_repository_dependency:
                    self.tpm.add_to_tool_panel(tool_shed_repository.name,
                                               repository_clone_url,
                                               tool_shed_repository.installed_changeset_revision,
                                               repository_tools_tups,
                                               self.repository_owner,
                                               self.migrated_tools_config,
                                               tool_panel_dict=tool_panel_dict_for_display,
                                               new_install=True)
        if install_dependencies and tool_dependencies and has_tool_dependencies:
            # Install tool dependencies.
            irm = install_manager.InstallRepositoryManager(self.app, self.tpm)
            itdm = install_manager.InstallToolDependencyManager(self.app)
            irm.update_tool_shed_repository_status(tool_shed_repository,
                                                   self.app.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES)
            # Get the tool_dependencies.xml file from disk.
            tool_dependencies_config = hg_util.get_config_from_disk('tool_dependencies.xml', repo_install_dir)
            installed_tool_dependencies = itdm.install_specified_tool_dependencies(tool_shed_repository=tool_shed_repository,
                                                                                   tool_dependencies_config=tool_dependencies_config,
                                                                                   tool_dependencies=tool_dependencies,
                                                                                   from_tool_migration_manager=True)
            for installed_tool_dependency in installed_tool_dependencies:
                if installed_tool_dependency.status == self.app.install_model.ToolDependency.installation_status.ERROR:
                    log.error(
                        'The ToolMigrationManager returned the following error while installing tool dependency %s: %s',
                        installed_tool_dependency.name, installed_tool_dependency.error_message)
        if 'datatypes' in irmm_metadata_dict:
            cdl = custom_datatype_manager.CustomDatatypeLoader(self.app)
            tool_shed_repository.status = self.app.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
            if not tool_shed_repository.includes_datatypes:
                tool_shed_repository.includes_datatypes = True
            self.app.install_model.context.add(tool_shed_repository)
            self.app.install_model.context.flush()
            work_dir = tempfile.mkdtemp(prefix="tmp-toolshed-hrc")
            datatypes_config = hg_util.get_config_from_disk(suc.DATATYPES_CONFIG_FILENAME, repo_install_dir)
            # Load proprietary data types required by tools.  The value of override is not
            # important here since the Galaxy server will be started after this installation
            # completes.
            converter_path, display_path = \
                cdl.alter_config_and_load_prorietary_datatypes(datatypes_config,
                                                               repo_install_dir,
                                                               override=False)
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = \
                    cdl.create_repository_dict_for_proprietary_datatypes(tool_shed=self.tool_shed_url,
                                                                         name=tool_shed_repository.name,
                                                                         owner=self.repository_owner,
                                                                         installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                         tool_dicts=irmm_metadata_dict.get('tools', []),
                                                                         converter_path=converter_path,
                                                                         display_path=display_path)
            if converter_path:
                # Load proprietary datatype converters
                self.app.datatypes_registry.load_datatype_converters(self.toolbox,
                                                                     installed_repository_dict=repository_dict)
            if display_path:
                # Load proprietary datatype display applications
                self.app.datatypes_registry.load_display_applications(self.app, installed_repository_dict=repository_dict)
            basic_util.remove_dir(work_dir)

    def install_repository(self, repository_elem, tool_shed_repository, install_dependencies, is_repository_dependency=False):
        """Install a single repository, loading contained tools into the tool panel."""
        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<installed changeset revision>
        relative_clone_dir = os.path.join(tool_shed_repository.tool_shed,
                                          'repos',
                                          tool_shed_repository.owner,
                                          tool_shed_repository.name,
                                          tool_shed_repository.installed_changeset_revision)
        clone_dir = os.path.join(self.tool_path, relative_clone_dir)
        cloned_ok = self.__iscloned(clone_dir)
        is_installed = False
        # Any of the following states should count as installed in this context.
        if tool_shed_repository.status in [self.app.install_model.ToolShedRepository.installation_status.INSTALLED,
                                           self.app.install_model.ToolShedRepository.installation_status.ERROR,
                                           self.app.install_model.ToolShedRepository.installation_status.UNINSTALLED,
                                           self.app.install_model.ToolShedRepository.installation_status.DEACTIVATED]:
            is_installed = True
        if cloned_ok and is_installed:
            log.info("Skipping automatic install of repository '%s' because it has already been installed in location %s",
                     tool_shed_repository.name, clone_dir)
        else:
            irm = install_manager.InstallRepositoryManager(self.app, self.tpm)
            repository_clone_url = os.path.join(self.tool_shed_url, 'repos', tool_shed_repository.owner, tool_shed_repository.name)
            relative_install_dir = os.path.join(relative_clone_dir, tool_shed_repository.name)
            install_dir = os.path.join(clone_dir, tool_shed_repository.name)
            ctx_rev = suc.get_ctx_rev(self.app,
                                      self.tool_shed_url,
                                      tool_shed_repository.name,
                                      tool_shed_repository.owner,
                                      tool_shed_repository.installed_changeset_revision)
            if not cloned_ok:
                irm.update_tool_shed_repository_status(tool_shed_repository,
                                                       self.app.install_model.ToolShedRepository.installation_status.CLONING)
                cloned_ok, error_message = hg_util.clone_repository(repository_clone_url, os.path.abspath(install_dir), ctx_rev)
            if cloned_ok and not is_installed:
                self.handle_repository_contents(tool_shed_repository=tool_shed_repository,
                                                repository_clone_url=repository_clone_url,
                                                relative_install_dir=relative_install_dir,
                                                repository_elem=repository_elem,
                                                install_dependencies=install_dependencies,
                                                is_repository_dependency=is_repository_dependency)
                self.app.install_model.context.refresh(tool_shed_repository)
                irm.update_tool_shed_repository_status(tool_shed_repository,
                                                       self.app.install_model.ToolShedRepository.installation_status.INSTALLED)
            else:
                log.error('Error attempting to clone repository %s: %s', str(tool_shed_repository.name), str(error_message))
                irm.update_tool_shed_repository_status(tool_shed_repository,
                                                       self.app.install_model.ToolShedRepository.installation_status.ERROR,
                                                       error_message=error_message)

    @property
    def non_shed_tool_panel_configs(self):
        return common_util.get_non_shed_tool_panel_configs(self.app)

    def order_repositories_for_installation(self, tool_shed_repositories, repository_dependencies_dict):
        """
        Some repositories may have repository dependencies that are required to be installed before the dependent
        repository.  This method will inspect the list of repositories about to be installed and make sure to order
        them appropriately.  For each repository about to be installed, if required repositories are not contained
        in the list of repositories about to be installed, then they are not considered.  Repository dependency
        definitions that contain circular dependencies should not result in an infinite loop, but obviously prior
        installation will not be handled for one or more of the repositories that require prior installation.  This
        process is similar to the process used when installing tool shed repositories, but does not handle managing
        tool panel sections and other components since repository dependency definitions contained in tool shed
        repositories with migrated tools must never define a relationship to a repository dependency that contains
        a tool.
        """
        ordered_tool_shed_repositories = []
        ordered_tsr_ids = []
        processed_tsr_ids = []
        prior_install_required_dict = self.get_prior_install_required_dict(tool_shed_repositories, repository_dependencies_dict)
        while len(processed_tsr_ids) != len(prior_install_required_dict.keys()):
            tsr_id = suc.get_next_prior_import_or_install_required_dict_entry(prior_install_required_dict, processed_tsr_ids)
            processed_tsr_ids.append(tsr_id)
            # Create the ordered_tsr_ids, the ordered_repo_info_dicts and the ordered_tool_panel_section_keys lists.
            if tsr_id not in ordered_tsr_ids:
                prior_install_required_ids = prior_install_required_dict[tsr_id]
                for prior_install_required_id in prior_install_required_ids:
                    if prior_install_required_id not in ordered_tsr_ids:
                        # Install the associated repository dependency first.
                        ordered_tsr_ids.append(prior_install_required_id)
                ordered_tsr_ids.append(tsr_id)
        for ordered_tsr_id in ordered_tsr_ids:
            for tool_shed_repository in tool_shed_repositories:
                if tool_shed_repository.id == ordered_tsr_id:
                    ordered_tool_shed_repositories.append(tool_shed_repository)
                    break
        return ordered_tool_shed_repositories

    def __has_tool_dependencies(self, metadata_dict):
        '''Determine if the provided metadata_dict specifies tool dependencies.'''
        # The use of the orphan_tool_dependencies category in metadata has been deprecated, but we still need to check in case
        # the metadata is out of date.
        if 'tool_dependencies' in metadata_dict or 'orphan_tool_dependencies' in metadata_dict:
            return True
        return False

    def __iscloned(self, clone_dir):
        full_path = os.path.abspath(clone_dir)
        if os.path.exists(full_path):
            for root, dirs, files in os.walk(full_path):
                if '.hg' in dirs:
                    # Assume that the repository has been installed if we find a .hg directory.
                    return True
        return False

    def __is_repository_dependency(self, name, changeset_revision, tool_shed_repository):
        '''Determine if the provided tool shed repository is a repository dependency.'''
        if str(tool_shed_repository.name) != str(name) or \
                str(tool_shed_repository.owner) != str(self.repository_owner) or \
                str(tool_shed_repository.changeset_revision) != str(changeset_revision):
            return True
        return False

    def __is_valid_repository_tag(self, elem):
        # <repository name="emboss_datatypes" description="Datatypes for Emboss tools" changeset_revision="a89163f31369" />
        if elem.tag != 'repository':
            return False
        if not elem.get('name'):
            return False
        if not elem.get('changeset_revision'):
            return False
        return True
