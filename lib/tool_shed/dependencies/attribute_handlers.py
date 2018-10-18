import copy
import logging

from galaxy.util import asbool
from galaxy.util.odict import odict
from galaxy.web import url_for
from tool_shed.dependencies.tool import tag_attribute_handler
from tool_shed.repository_types.util import REPOSITORY_DEPENDENCY_DEFINITION_FILENAME
from tool_shed.repository_types.util import TOOL_DEPENDENCY_DEFINITION_FILENAME
from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import repository_util
from tool_shed.util import xml_util

log = logging.getLogger(__name__)


class RepositoryDependencyAttributeHandler(object):

    def __init__(self, app, unpopulate):
        self.app = app
        self.file_name = REPOSITORY_DEPENDENCY_DEFINITION_FILENAME
        self.unpopulate = unpopulate

    def check_tag_attributes(self, elem):
        # <repository name="molecule_datatypes" owner="test" />
        error_message = ''
        name = elem.get('name')
        if not name:
            error_message += 'The tag is missing the required name attribute.  '
        owner = elem.get('owner')
        if not owner:
            error_message += 'The tag is missing the required owner attribute.  '
        log.debug(error_message)
        return error_message

    def handle_complex_dependency_elem(self, parent_elem, elem_index, elem):
        """
        Populate or unpopulate the toolshed and changeset_revision attributes of a
        <repository> tag that defines a complex repository dependency.
        """
        # <repository name="package_eigen_2_0" owner="test" prior_installation_required="True" />
        altered, new_elem, error_message = self.handle_elem(elem)
        if error_message:
            error_message += '  The %s file contains an invalid <repository> tag.' % TOOL_DEPENDENCY_DEFINITION_FILENAME
        return altered, new_elem, error_message

    def handle_elem(self, elem):
        """Populate or unpopulate the changeset_revision and toolshed attributes of repository tags."""
        # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
        # <repository changeset_revision="xxx" name="package_xorg_macros_1_17_1" owner="test" toolshed="yyy">
        #    <package name="xorg_macros" version="1.17.1" />
        # </repository>
        error_message = ''
        name = elem.get('name')
        owner = elem.get('owner')
        # The name and owner attributes are always required, so if either are missing, return the error message.
        if not name or not owner:
            error_message = self.check_tag_attributes(elem)
            return False, elem, error_message
        altered = False
        toolshed = elem.get('toolshed')
        changeset_revision = elem.get('changeset_revision')
        # Over a short period of time a bug existed which caused the prior_installation_required attribute
        # to be set to False and included in the <repository> tag when a repository was exported along with
        # its dependencies.  The following will eliminate this problematic attribute upon import.
        prior_installation_required = elem.get('prior_installation_required')
        if prior_installation_required is not None and not asbool(prior_installation_required):
            del elem.attrib['prior_installation_required']
        sub_elems = [child_elem for child_elem in list(elem)]
        if len(sub_elems) > 0:
            # At this point, a <repository> tag will point only to a package.
            # <package name="xorg_macros" version="1.17.1" />
            # Coerce the list to an odict().
            sub_elements = odict()
            packages = []
            for sub_elem in sub_elems:
                sub_elem_type = sub_elem.tag
                sub_elem_name = sub_elem.get('name')
                sub_elem_version = sub_elem.get('version')
                if sub_elem_type and sub_elem_name and sub_elem_version:
                    packages.append((sub_elem_name, sub_elem_version))
            sub_elements['packages'] = packages
        else:
            # Set to None.
            sub_elements = None
        if self.unpopulate:
            # We're exporting the repository, so eliminate all toolshed and changeset_revision attributes
            # from the <repository> tag.
            if toolshed or changeset_revision:
                attributes = odict()
                attributes['name'] = name
                attributes['owner'] = owner
                prior_installation_required = elem.get('prior_installation_required')
                if asbool(prior_installation_required):
                    attributes['prior_installation_required'] = 'True'
                new_elem = xml_util.create_element('repository', attributes=attributes, sub_elements=sub_elements)
                altered = True
            return altered, new_elem, error_message
        # From here on we're populating the toolshed and changeset_revision attributes if necessary.
        if not toolshed:
            # Default the setting to the current tool shed.
            toolshed = str(url_for('/', qualified=True)).rstrip('/')
            elem.attrib['toolshed'] = toolshed
            altered = True
        if not changeset_revision:
            # Populate the changeset_revision attribute with the latest installable metadata revision for
            # the defined repository.  We use the latest installable revision instead of the latest metadata
            # revision to ensure that the contents of the revision are valid.
            repository = repository_util.get_repository_by_name_and_owner(self.app, name, owner)
            if repository:
                lastest_installable_changeset_revision = \
                    metadata_util.get_latest_downloadable_changeset_revision(self.app, repository)
                if lastest_installable_changeset_revision != hg_util.INITIAL_CHANGELOG_HASH:
                    elem.attrib['changeset_revision'] = lastest_installable_changeset_revision
                    altered = True
                else:
                    error_message = 'Invalid latest installable changeset_revision %s ' % \
                        str(lastest_installable_changeset_revision)
                    error_message += 'retrieved for repository %s owned by %s.  ' % (str(name), str(owner))
            else:
                error_message = 'Unable to locate repository with name %s and owner %s.  ' % (str(name), str(owner))
        return altered, elem, error_message

    def handle_sub_elem(self, parent_elem, elem_index, elem):
        """
        Populate or unpopulate the toolshed and changeset_revision attributes for each of
        the following tag sets.
        <action type="set_environment_for_install">
        <action type="setup_r_environment">
        <action type="setup_ruby_environment">
        """
        sub_elem_altered = False
        error_message = ''
        for sub_index, sub_elem in enumerate(elem):
            # Make sure to skip comments and tags that are not <repository>.
            if sub_elem.tag == 'repository':
                altered, new_sub_elem, message = self.handle_elem(sub_elem)
                if message:
                    error_message += 'The %s file contains an invalid <repository> tag.  %s' % \
                        (TOOL_DEPENDENCY_DEFINITION_FILENAME, message)
                if altered:
                    if not sub_elem_altered:
                        sub_elem_altered = True
                    elem[sub_index] = new_sub_elem
        if sub_elem_altered:
            parent_elem[elem_index] = elem
        return sub_elem_altered, parent_elem, error_message

    def handle_tag_attributes(self, config):
        """
        Populate or unpopulate the toolshed and changeset_revision attributes of a
        <repository> tag.  Populating will occur when a dependency definition file
        is being uploaded to the repository, while unpopulating will occur when the
        repository is being exported.
        """
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree, error_message = xml_util.parse_xml(config)
        if tree is None:
            return False, None, error_message
        root = tree.getroot()
        root_altered = False
        new_root = copy.deepcopy(root)
        for index, elem in enumerate(root):
            if elem.tag == 'repository':
                # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
                altered, new_elem, error_message = self.handle_elem(elem)
                if error_message:
                    error_message = 'The %s file contains an invalid <repository> tag.  %s' % (self.file_name, error_message)
                    return False, None, error_message
                if altered:
                    if not root_altered:
                        root_altered = True
                    new_root[index] = new_elem
        return root_altered, new_root, error_message


class ToolDependencyAttributeHandler(object):

    def __init__(self, app, unpopulate):
        self.app = app
        self.file_name = TOOL_DEPENDENCY_DEFINITION_FILENAME
        self.unpopulate = unpopulate

    def handle_tag_attributes(self, tool_dependencies_config):
        """
        Populate or unpopulate the tooshed and changeset_revision attributes of each <repository>
        tag defined within a tool_dependencies.xml file.
        """
        rdah = RepositoryDependencyAttributeHandler(self.app, self.unpopulate)
        tah = tag_attribute_handler.TagAttributeHandler(self.app, rdah, self.unpopulate)
        altered = False
        error_message = ''
        # Make sure we're looking at a valid tool_dependencies.xml file.
        tree, error_message = xml_util.parse_xml(tool_dependencies_config)
        if tree is None:
            return False, None, error_message
        root = tree.getroot()
        altered, new_root, error_message = tah.process_config(root, skip_actions_tags=False)
        return altered, new_root, error_message
