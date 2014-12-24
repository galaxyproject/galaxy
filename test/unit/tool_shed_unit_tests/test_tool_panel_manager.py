import os

from galaxy.util import parse_xml

from tools.test_toolbox import BaseToolBoxTestCase
from tool_shed.galaxy_install.tools import tool_panel_manager


class ToolPanelManagerTestCase( BaseToolBoxTestCase ):

    def test_handle_tool_panel_section( self ):
        self._init_tool()
        self._add_config( """<toolbox><section id="tid" name="test"><tool file="tool.xml" /></section></toolbox>""" )
        toolbox = self.toolbox
        tpm = tool_panel_manager.ToolPanelManager( self.app )
        # Test fetch existing section by id.
        section_id, section = tpm.handle_tool_panel_section( toolbox, tool_panel_section_id="tid" )
        assert section_id == "tid"
        assert len( section.elems ) == 1  # tool.xml
        assert section.id == "tid"
        assert len( toolbox.tool_panel ) == 1

        section_id, section = tpm.handle_tool_panel_section( toolbox, new_tool_panel_section_label="tid2" )
        assert section_id == "tid2"
        assert len( section.elems ) == 0  # new section
        assert section.id == "tid2"
        assert len( toolbox.tool_panel ) == 2

        # Test re-fetch new section by same id.
        section_id, section = tpm.handle_tool_panel_section( toolbox, new_tool_panel_section_label="tid2" )
        assert section_id == "tid2"
        assert len( section.elems ) == 0  # new section
        assert section.id == "tid2"
        assert len( toolbox.tool_panel ) == 2

    def test_add_tool_to_panel( self ):
        self._init_tool()
        self._add_config( """<toolbox tool_path="%s"></toolbox>""" % self.test_directory )
        tool_path = os.path.join(self.test_directory, "tool.xml")
        self.tool.guid = "123456"
        new_tools = [{"guid": "123456", "tool_config": tool_path}]
        repository_tools_tups = [
            (
                tool_path,
                "123456",
                self.tool,
            )
        ]
        _, section = self.toolbox.get_or_create_section("tid1")
        tpm = tool_panel_manager.ToolPanelManager( self.app )
        tool_panel_dict = tpm.generate_tool_panel_dict_for_new_install(
            tool_dicts=new_tools,
            tool_section=section,
        )
        tpm.add_to_tool_panel(
            repository_name="test_repo",
            repository_clone_url="http://github.com/galaxyproject/example.git",
            changeset_revision="0123456789abcde",
            repository_tools_tups=repository_tools_tups,
            owner="devteam",
            shed_tool_conf="tool_conf.xml",
            tool_panel_dict=tool_panel_dict,
        )
        self._assert_valid_xml( self.integerated_tool_panel_path )
        self._assert_valid_xml( os.path.join( self.test_directory, "tool_conf.xml" ) )

    def _assert_valid_xml( self, filename ):
        try:
            parse_xml( filename )
        except Exception:
            message_template = "file %s does not contain valid XML, content %s"
            message = message_template % ( filename, open( filename, "r" ).read() )
            raise AssertionError( message )
