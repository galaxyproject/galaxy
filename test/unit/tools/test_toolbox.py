import json
import os
import string
import unittest

import routes
from six import string_types

import tools_support
from galaxy import model
from galaxy.model import tool_shed_install
from galaxy.model.tool_shed_install import mapping
from galaxy.tools import ToolBox
from galaxy.tools.toolbox.lineages.tool_shed import ToolVersionCache
from galaxy.tools.toolbox.watcher import get_tool_conf_watcher

from .test_toolbox_filters import mock_trans


CONFIG_TEST_TOOL_VERSION_TEMPLATE = string.Template(
    """    <tool file="tool.xml" guid="github.com/galaxyproject/example/test_tool/0.${version}">
            <tool_shed>github.com</tool_shed>
            <repository_name>example</repository_name>
            <repository_owner>galaxyproject</repository_owner>
            <installed_changeset_revision>${version}</installed_changeset_revision>
            <id>github.com/galaxyproject/example/test_tool/0.${version}</id>
            <version>0.${version}</version>
        </tool>
    """
)
CONFIG_TEST_TOOL_VERSION_1 = CONFIG_TEST_TOOL_VERSION_TEMPLATE.safe_substitute( dict( version="1" ) )
CONFIG_TEST_TOOL_VERSION_2 = CONFIG_TEST_TOOL_VERSION_TEMPLATE.safe_substitute( dict( version="2" ) )


class BaseToolBoxTestCase(  unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools  ):

    @property
    def integerated_tool_panel_path( self ):
        return os.path.join(self.test_directory, "integrated_tool_panel.xml")

    def assert_integerated_tool_panel( self, exists=True ):
        does_exist = os.path.exists( self.integerated_tool_panel_path )
        if exists:
            assert does_exist
        else:
            assert not does_exist

    @property
    def toolbox( self ):
        if self.__toolbox is None:
            self.__toolbox = SimplifiedToolBox( self )
            # wire app with this new toolbox
            self.app.toolbox = self.__toolbox
        return self.__toolbox

    def setUp( self ):
        self.reindexed = False
        self.setup_app( mock_model=False )
        install_model = mapping.init( "sqlite:///:memory:", create_tables=True )
        self.app.install_model = install_model
        self.app.reindex_tool_search = self.__reindex
        itp_config = os.path.join(self.test_directory, "integrated_tool_panel.xml")
        self.app.config.integrated_tool_panel_config = itp_config
        self.__toolbox = None
        self.config_files = []

    def _repo_install( self, changeset ):
        repository = tool_shed_install.ToolShedRepository()
        repository.tool_shed = "github.com"
        repository.owner = "galaxyproject"
        repository.name = "example"
        repository.changeset_revision = changeset
        repository.installed_changeset_revision = changeset
        repository.deleted = False
        repository.uninstalled = False
        self.app.install_model.context.add( repository )
        self.app.install_model.context.flush( )
        self.app.tool_version_cache = ToolVersionCache(self.app)
        return repository

    def _setup_two_versions( self ):
        repository1 = self._repo_install( changeset="1" )
        version1 = tool_shed_install.ToolVersion()
        version1.tool_id = "github.com/galaxyproject/example/test_tool/0.1"
        version1.repository = repository1
        self.app.install_model.context.add( version1 )
        self.app.install_model.context.flush( )

        repository2 = self._repo_install( changeset="2" )
        version2 = tool_shed_install.ToolVersion()
        version2.tool_id = "github.com/galaxyproject/example/test_tool/0.2"
        version2.repository = repository2

        self.app.install_model.context.add( version2 )
        self.app.install_model.context.flush( )

        version_association = tool_shed_install.ToolVersionAssociation()
        version_association.parent_id = version1.id
        version_association.tool_id = version2.id

        self.app.install_model.context.add( version_association )
        self.app.install_model.context.flush( )
        self.app.tool_version_cache = ToolVersionCache(self.app)

    def _setup_two_versions_in_config( self, section=False ):
        if section:
            template = """<toolbox tool_path="%s">
<section id="tid" name="TID" version="">
    %s
</section>
<section id="tid" name="TID" version="">
    %s
</section>
</toolbox>"""
        else:
            template = """<toolbox tool_path="%s">
<section id="tid" name="TID" version="">
    %s
</section>
<section id="tid" name="TID" version="">
    %s
</section>
</toolbox>"""
        self._add_config( template % (self.test_directory, CONFIG_TEST_TOOL_VERSION_1, CONFIG_TEST_TOOL_VERSION_2 ) )

    def _add_config( self, content, name="tool_conf.xml" ):
        is_json = name.endswith(".json")
        path = self._tool_conf_path( name=name )
        with open( path, "w" ) as f:
            if not is_json or isinstance(content, string_types):
                f.write( content )
            else:
                json.dump(content, f)
        self.config_files.append( path )

    def _tool_conf_path( self, name="tool_conf.xml" ):
        path = os.path.join( self.test_directory, name )
        return path

    def _tool_path( self, name="tool.xml" ):
        path = os.path.join( self.test_directory, name )
        return path

    def __reindex( self ):
        self.reindexed = True


class ToolBoxTestCase( BaseToolBoxTestCase ):

    def test_load_file( self ):
        self._init_tool()
        self._add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None
        assert toolbox.get_tool( "not_a_test_tool" ) is None

    def test_to_dict_in_panel( self ):
        for json_conf in [True, False]:
            self._init_tool_in_section(json=json_conf)
            mapper = routes.Mapper()
            mapper.connect( "tool_runner", "/test/tool_runner" )
            as_dict = self.toolbox.to_dict( mock_trans() )
            test_section = self._find_section(as_dict, "t")
            assert len(test_section["elems"]) == 1
            assert test_section["elems"][0]["id"] == "test_tool"

    def test_to_dict_out_of_panel( self ):
        for json_conf in [True, False]:
            self._init_tool_in_section(json=json_conf)
            mapper = routes.Mapper()
            mapper.connect( "tool_runner", "/test/tool_runner" )
            as_dict = self.toolbox.to_dict( mock_trans(), in_panel=False )
            assert as_dict[0]["id"] == "test_tool"

    def test_out_of_panel_filtering( self ):
        self._init_tool_in_section()

        mapper = routes.Mapper()
        mapper.connect( "tool_runner", "/test/tool_runner" )
        as_dict = self.toolbox.to_dict( mock_trans(), in_panel=False )
        assert len(as_dict) == 1

        def allow_user_access(user, attempting_access):
            assert not attempting_access
            return False

        # Disable access to the tool, make sure it is filtered out.
        self.toolbox.get_tool("test_tool").allow_user_access = allow_user_access
        as_dict = self.toolbox.to_dict( mock_trans(), in_panel=False )
        assert len(as_dict) == 0

    def _find_section( self, as_dict, section_id ):
        for elem in as_dict:
            if elem.get("id") == section_id:
                assert elem["model_class"] == "ToolSection"
                return elem
        assert False, "Failed to find section with id [%s]" % section_id

    def test_tool_shed_properties( self ):
        self._init_tool()
        self._setup_two_versions_in_config( section=False )
        self._setup_two_versions()

        test_tool = self.toolbox.get_tool( "test_tool" )
        assert test_tool.tool_shed == "github.com"
        assert test_tool.repository_owner == "galaxyproject"
        assert test_tool.repository_name == "example"
        # TODO: Not deterministc, probably should be?
        assert test_tool.installed_changeset_revision in ["1", "2"]

    def test_tool_shed_properties_only_on_installed_tools( self ):
        self._init_tool()
        self._add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )
        toolbox = self.toolbox
        test_tool = toolbox.get_tool( "test_tool" )
        assert test_tool.tool_shed is None
        assert test_tool.repository_name is None
        assert test_tool.repository_owner is None
        assert test_tool.installed_changeset_revision is None

    def test_load_file_in_section( self ):
        self._init_tool_in_section()

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None
        assert toolbox.get_tool( "not_a_test_tool" ) is None

    def test_writes_integrate_tool_panel( self ):
        self._init_tool()
        self._add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )

        self.assert_integerated_tool_panel(exists=False)
        self.toolbox
        self.assert_integerated_tool_panel(exists=True)

    def test_groups_tools_in_section( self ):
        self._init_tool()
        self._setup_two_versions_in_config( section=True )
        self._setup_two_versions()
        self.toolbox
        self.__verify_two_test_tools( )

        # Assert only newer version of the tool loaded into the panel.
        section = self.toolbox._tool_panel["tid"]
        assert len(section.elems) == 1
        assert next(iter(section.elems.values())).id == "github.com/galaxyproject/example/test_tool/0.2"

    def test_group_tools_out_of_section( self ):
        self._init_tool()
        self._setup_two_versions_in_config( section=False )
        self._setup_two_versions()
        self.__verify_two_test_tools( )

        # Assert tools merged in tool panel.
        assert len( self.toolbox._tool_panel ) == 1

    def test_get_tool_id( self ):
        self._init_tool()
        self._setup_two_versions_in_config( )
        self._setup_two_versions()
        assert self.toolbox.get_tool_id( "test_tool" ) in [
            "github.com/galaxyproject/example/test_tool/0.1",
            "github.com/galaxyproject/example/test_tool/0.2"
        ]
        assert self.toolbox.get_tool_id( "github.com/galaxyproject/example/test_tool/0.1" ) == "github.com/galaxyproject/example/test_tool/0.1"
        assert self.toolbox.get_tool_id( "github.com/galaxyproject/example/test_tool/0.2" ) == "github.com/galaxyproject/example/test_tool/0.2"
        assert self.toolbox.get_tool_id( "github.com/galaxyproject/example/test_tool/0.3" ) is None

    def test_tool_dir( self ):
        self._init_tool()
        self._add_config( """<toolbox><tool_dir dir="%s" /></toolbox>""" % self.test_directory )

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None

    def test_tool_dir_json( self ):
        self._init_tool()
        self._add_config({"items": [{"type": "tool_dir", "dir": self.test_directory}]}, name="tool_conf.json")

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None

    def test_workflow_in_panel( self ):
        stored_workflow = self.__test_workflow()
        encoded_id = self.app.security.encode_id( stored_workflow.id )
        self._add_config( """<toolbox><workflow id="%s" /></toolbox>""" % encoded_id )
        assert len( self.toolbox._tool_panel ) == 1
        panel_workflow = next(iter(self.toolbox._tool_panel.values()))
        assert panel_workflow == stored_workflow.latest_workflow
        # TODO: test to_dict with workflows

    def test_workflow_in_section( self ):
        stored_workflow = self.__test_workflow()
        encoded_id = self.app.security.encode_id( stored_workflow.id )
        self._add_config( """<toolbox><section id="tid" name="TID"><workflow id="%s" /></section></toolbox>""" % encoded_id )
        assert len( self.toolbox._tool_panel ) == 1
        section = self.toolbox._tool_panel[ 'tid' ]
        assert len( section.elems ) == 1
        panel_workflow = next(iter(section.elems.values()))
        assert panel_workflow == stored_workflow.latest_workflow

    def test_label_in_panel( self ):
        self._add_config( """<toolbox><label id="lab1" text="Label 1" /><label id="lab2" text="Label 2" /></toolbox>""" )
        assert len( self.toolbox._tool_panel ) == 2
        self.__check_test_labels( self.toolbox._tool_panel )

    def test_label_in_section( self ):
        self._add_config( """<toolbox><section id="tid" name="TID"><label id="lab1" text="Label 1" /><label id="lab2" text="Label 2" /></section></toolbox>""" )
        assert len( self.toolbox._tool_panel ) == 1
        section = self.toolbox._tool_panel[ 'tid' ]
        self.__check_test_labels( section.elems )

    def _init_tool_in_section( self, json=False ):
        self._init_tool()
        if not json:
            self._add_config( """<toolbox><section id="t" name="test"><tool file="tool.xml" /></section></toolbox>""" )
        else:
            section = {
                "type": "section",
                "id": "t",
                "name": "test",
                "items": [{"type": "tool",
                           "file": "tool.xml"}],
            }
            self._add_config({"items": [section]}, name="tool_conf.json")

    def __check_test_labels( self, panel_dict ):
        assert list(panel_dict.keys()) == ["label_lab1", "label_lab2"]
        label1 = next(iter(panel_dict.values()))
        assert label1.id == "lab1"
        assert label1.text == "Label 1"

        label2 = panel_dict[ "label_lab2" ]
        assert label2.id == "lab2"
        assert label2.text == "Label 2"

    def __test_workflow( self ):
        stored_workflow = model.StoredWorkflow()
        workflow = model.Workflow()
        workflow.stored_workflow = stored_workflow
        stored_workflow.latest_workflow = workflow
        user = model.User()
        user.email = "test@example.com"
        user.password = "passw0rD1"
        stored_workflow.user = user
        self.app.model.context.add( workflow )
        self.app.model.context.add( stored_workflow )
        self.app.model.context.flush()
        return stored_workflow

    def __verify_two_test_tools( self ):
        # Assert tool versions of the tool with simple id 'test_tool'
        all_versions = self.toolbox.get_tool( "test_tool", get_all_versions=True )
        assert len( all_versions ) == 2

        # Verify lineage_ids on both tools is correctly ordered.
        for version in ["0.1", "0.2"]:
            guid = "github.com/galaxyproject/example/test_tool/" + version
            lineage_ids = self.toolbox.get_tool( guid ).lineage.get_version_ids()
            assert lineage_ids[ 0 ] == "github.com/galaxyproject/example/test_tool/0.1"
            assert lineage_ids[ 1 ] == "github.com/galaxyproject/example/test_tool/0.2"

        # Test tool_version attribute.
        assert self.toolbox.get_tool( "test_tool", tool_version="0.1" ).guid == "github.com/galaxyproject/example/test_tool/0.1"
        assert self.toolbox.get_tool( "test_tool", tool_version="0.2" ).guid == "github.com/galaxyproject/example/test_tool/0.2"

    def test_default_lineage( self ):
        self.__init_versioned_tools()
        self._add_config( """<toolbox><tool file="tool_v01.xml" /><tool file="tool_v02.xml" /></toolbox>""" )
        self.__verify_get_tool_for_default_lineage()

    def test_default_lineage_reversed( self ):
        # Run same test as above but with entries in tool_conf reversed to
        # ensure versioning is at work and not order effects.
        self.__init_versioned_tools()
        self._add_config( """<toolbox><tool file="tool_v02.xml" /><tool file="tool_v01.xml" /></toolbox>""" )
        self.__verify_get_tool_for_default_lineage()

    def test_grouping_with_default_lineage( self ):
        self.__init_versioned_tools()
        self._add_config( """<toolbox><tool file="tool_v01.xml" /><tool file="tool_v02.xml" /></toolbox>""" )
        self.__verify_tool_panel_for_default_lineage()

    def test_grouping_with_default_lineage_reversed( self ):
        # Run same test as above but with entries in tool_conf reversed to
        # ensure versioning is at work and not order effects.
        self.__init_versioned_tools()
        self._add_config( """<toolbox><tool file="tool_v02.xml" /><tool file="tool_v02.xml" /></toolbox>""" )
        self.__verify_tool_panel_for_default_lineage()

    def __init_versioned_tools( self ):
        self._init_tool( filename="tool_v01.xml", version="0.1" )
        self._init_tool( filename="tool_v02.xml", version="0.2" )

    def __verify_tool_panel_for_default_lineage( self ):
        assert len( self.toolbox._tool_panel ) == 1
        tool = self.toolbox._tool_panel["tool_test_tool"]
        assert tool.version == "0.2", tool.version
        assert tool.id == "test_tool"

    def __verify_get_tool_for_default_lineage( self ):
        tool_v01 = self.toolbox.get_tool( "test_tool", tool_version="0.1" )
        tool_v02 = self.toolbox.get_tool( "test_tool", tool_version="0.2" )
        assert tool_v02.id == "test_tool"
        assert tool_v02.version == "0.2", tool_v02.version
        assert tool_v01.id == "test_tool"
        assert tool_v01.version == "0.1"

        # Newer variant gets to be default for that id.
        default_tool = self.toolbox.get_tool( "test_tool" )
        assert default_tool.id == "test_tool"
        assert default_tool.version == "0.2"

    def __remove_itp( self ):
        os.remove( os.path)

    def __setup_shed_tool_conf( self ):
        self._add_config( """<toolbox tool_path="."></toolbox>""" )

        self.toolbox  # create toolbox
        assert not self.reindexed

        os.remove( self.integerated_tool_panel_path )


class SimplifiedToolBox( ToolBox ):

    def __init__( self, test_case ):
        app = test_case.app
        # Handle app/config stuff needed by toolbox but not by tools.
        app.job_config.get_tool_resource_parameters = lambda tool_id: None
        app.config.update_integrated_tool_panel = True
        config_files = test_case.config_files
        tool_root_dir = test_case.test_directory
        super( SimplifiedToolBox, self ).__init__(
            config_files,
            tool_root_dir,
            app,
        )
        self._tool_conf_watcher = get_tool_conf_watcher(dummy_callback)

    def handle_panel_update(self, section_dict):
        self.create_section(section_dict)


def dummy_callback():
    pass
