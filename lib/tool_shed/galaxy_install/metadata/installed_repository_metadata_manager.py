import logging
import os

from sqlalchemy import false

from galaxy import util
from galaxy.util import inflector
from galaxy.web.form_builder import SelectField
from tool_shed.galaxy_install.tools import tool_panel_manager
from tool_shed.metadata import metadata_generator
from tool_shed.util import common_util
from tool_shed.util import repository_util
from tool_shed.util import tool_util
from tool_shed.util import xml_util
log = logging.getLogger(__name__)


class InstalledRepositoryMetadataManager(metadata_generator.MetadataGenerator):

    def __init__(self, app, tpm=None, repository=None, changeset_revision=None, repository_clone_url=None,
                 shed_config_dict=None, relative_install_dir=None, repository_files_dir=None,
                 resetting_all_metadata_on_repository=False, updating_installed_repository=False,
                 persist=False, metadata_dict=None):
        super(InstalledRepositoryMetadataManager, self).__init__(app, repository, changeset_revision,
                                                                 repository_clone_url, shed_config_dict,
                                                                 relative_install_dir, repository_files_dir,
                                                                 resetting_all_metadata_on_repository,
                                                                 updating_installed_repository, persist,
                                                                 metadata_dict=metadata_dict, user=None)
        if tpm is None:
            self.tpm = tool_panel_manager.ToolPanelManager(self.app)
        else:
            self.tpm = tpm

    def build_repository_ids_select_field(self, name='repository_ids', multiple=True, display='checkboxes'):
        """Generate the current list of repositories for resetting metadata."""
        repositories_select_field = SelectField(name=name, multiple=multiple, display=display)
        query = self.get_query_for_setting_metadata_on_repositories(order=True)
        for repository in query:
            owner = str(repository.owner)
            option_label = '%s (%s)' % (str(repository.name), owner)
            option_value = '%s' % self.app.security.encode_id(repository.id)
            repositories_select_field.add_option(option_label, option_value)
        return repositories_select_field

    def get_query_for_setting_metadata_on_repositories(self, order=True):
        """
        Return a query containing repositories for resetting metadata.  The order parameter
        is used for displaying the list of repositories ordered alphabetically for display on
        a page.  When called from the Galaxy API, order is False.
        """
        if order:
            return self.app.install_model.context.query(self.app.install_model.ToolShedRepository) \
                                                 .filter(self.app.install_model.ToolShedRepository.table.c.uninstalled == false()) \
                                                 .order_by(self.app.install_model.ToolShedRepository.table.c.name,
                                                           self.app.install_model.ToolShedRepository.table.c.owner)
        else:
            return self.app.install_model.context.query(self.app.install_model.ToolShedRepository) \
                                                 .filter(self.app.install_model.ToolShedRepository.table.c.uninstalled == false())

    def get_repository_tools_tups(self):
        """
        Return a list of tuples of the form (relative_path, guid, tool) for each tool defined
        in the received tool shed repository metadata.
        """
        repository_tools_tups = []
        shed_conf_dict = self.tpm.get_shed_tool_conf_dict(self.metadata_dict.get('shed_config_filename'))
        if 'tools' in self.metadata_dict:
            for tool_dict in self.metadata_dict['tools']:
                load_relative_path = relative_path = tool_dict.get('tool_config', None)
                if shed_conf_dict.get('tool_path'):
                    load_relative_path = os.path.join(shed_conf_dict.get('tool_path'), relative_path)
                guid = tool_dict.get('guid', None)
                if relative_path and guid:
                    tool = self.app.toolbox.load_tool(os.path.abspath(load_relative_path), guid=guid, use_cached=False)
                else:
                    tool = None
                if tool:
                    repository_tools_tups.append((relative_path, guid, tool))
        return repository_tools_tups

    def reset_all_metadata_on_installed_repository(self):
        """Reset all metadata on a single tool shed repository installed into a Galaxy instance."""
        if self.relative_install_dir:
            original_metadata_dict = self.repository.metadata
            self.generate_metadata_for_changeset_revision()
            if self.metadata_dict != original_metadata_dict:
                self.repository.metadata = self.metadata_dict
                self.update_in_shed_tool_config()
                self.app.install_model.context.add(self.repository)
                self.app.install_model.context.flush()
                self.app.tool_shed_repository_cache.rebuild()
                log.debug('Metadata has been reset on repository %s.' % self.repository.name)
            else:
                log.debug('Metadata did not need to be reset on repository %s.' % self.repository.name)
        else:
            log.debug('Error locating installation directory for repository %s.' % self.repository.name)

    def reset_metadata_on_selected_repositories(self, user, **kwd):
        """
        Inspect the repository changelog to reset metadata for all appropriate changeset revisions.
        This method is called from both Galaxy and the Tool Shed.
        """
        repository_ids = util.listify(kwd.get('repository_ids', None))
        message = ''
        status = 'done'
        if repository_ids:
            successful_count = 0
            unsuccessful_count = 0
            for repository_id in repository_ids:
                try:
                    repository = repository_util.get_installed_tool_shed_repository(self.app, repository_id)
                    self.set_repository(repository)
                    self.reset_all_metadata_on_installed_repository()
                    if self.invalid_file_tups:
                        message = tool_util.generate_message_for_invalid_tools(self.app,
                                                                               self.invalid_file_tups,
                                                                               repository,
                                                                               None,
                                                                               as_html=False)
                        log.debug(message)
                        unsuccessful_count += 1
                    else:
                        log.debug("Successfully reset metadata on repository %s owned by %s" %
                            (str(repository.name), str(repository.owner)))
                        successful_count += 1
                except Exception:
                    log.exception("Error attempting to reset metadata on repository %s", str(repository.name))
                    unsuccessful_count += 1
            message = "Successfully reset metadata on %d %s.  " % \
                (successful_count, inflector.cond_plural(successful_count, "repository"))
            if unsuccessful_count:
                message += "Error setting metadata on %d %s - see the paster log for details.  " % \
                    (unsuccessful_count, inflector.cond_plural(unsuccessful_count, "repository"))
        else:
            message = 'Select at least one repository to on which to reset all metadata.'
            status = 'error'
        return message, status

    def set_repository(self, repository):
        super(InstalledRepositoryMetadataManager, self).set_repository(repository)
        self.repository_clone_url = common_util.generate_clone_url_for_installed_repository(self.app, repository)

    def tool_shed_from_repository_clone_url(self):
        """Given a repository clone URL, return the tool shed that contains the repository."""
        cleaned_repository_clone_url = common_util.remove_protocol_and_user_from_clone_url(self.repository_clone_url)
        return common_util.remove_protocol_and_user_from_clone_url(cleaned_repository_clone_url).split('/repos/')[0].rstrip('/')

    def update_in_shed_tool_config(self):
        """
        A tool shed repository is being updated so change the shed_tool_conf file.  Parse the config
        file to generate the entire list of config_elems instead of using the in-memory list.
        """
        shed_conf_dict = self.repository.get_shed_config_dict(self.app)
        shed_tool_conf = shed_conf_dict['config_filename']
        tool_path = shed_conf_dict['tool_path']
        self.tpm.generate_tool_panel_dict_from_shed_tool_conf_entries(self.repository)
        repository_tools_tups = self.get_repository_tools_tups()
        clone_url = common_util.generate_clone_url_for_installed_repository(self.app, self.repository)
        tool_shed = self.tool_shed_from_repository_clone_url()
        owner = self.repository.owner
        if not owner:
            cleaned_repository_clone_url = common_util.remove_protocol_and_user_from_clone_url(clone_url)
            owner = repository_util.get_repository_owner(cleaned_repository_clone_url)
        guid_to_tool_elem_dict = {}
        for tool_config_filename, guid, tool in repository_tools_tups:
            guid_to_tool_elem_dict[guid] = self.tpm.generate_tool_elem(tool_shed,
                                                                       self.repository.name,
                                                                       self.repository.changeset_revision,
                                                                       self.repository.owner or '',
                                                                       tool_config_filename,
                                                                       tool,
                                                                       None)
        config_elems = []
        tree, error_message = xml_util.parse_xml(shed_tool_conf)
        if tree:
            root = tree.getroot()
            for elem in root:
                if elem.tag == 'section':
                    for i, tool_elem in enumerate(elem):
                        guid = tool_elem.attrib.get('guid')
                        if guid in guid_to_tool_elem_dict:
                            elem[i] = guid_to_tool_elem_dict[guid]
                elif elem.tag == 'tool':
                    guid = elem.attrib.get('guid')
                    if guid in guid_to_tool_elem_dict:
                        elem = guid_to_tool_elem_dict[guid]
                config_elems.append(elem)
            self.tpm.config_elems_to_xml_file(config_elems, shed_tool_conf, tool_path)
