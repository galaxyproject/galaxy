import os
import unittest

from galaxy.tools import ToolBox
from galaxy.model.tool_shed_install import mapping
import tools_support


class ToolBoxTestCase( unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools ):

    def test_load_file( self ):
        self._init_tool()
        self.__add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None
        assert toolbox.get_tool( "not_a_test_tool" ) is None

    def test_load_file_in_section( self ):
        self._init_tool()
        self.__add_config( """<toolbox><section id="t" name="test"><tool file="tool.xml" /></section></toolbox>""" )

        toolbox = self.toolbox
        assert toolbox.get_tool( "test_tool" ) is not None
        assert toolbox.get_tool( "not_a_test_tool" ) is None

    def test_writes_integrate_tool_panel( self ):
        self._init_tool()
        self.__add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )

        itp = os.path.join(self.test_directory, "integrated_tool_panel.xml")

        assert not os.path.exists( itp )
        self.toolbox
        assert os.path.exists( itp )

    def test_groups_tools( self ):
        self._init_tool()
        self.__add_config( """<toolbox><tool file="tool.xml" /></toolbox>""" )

    def setUp( self ):
        self.setup_app( mock_model=False )
        itp_config = os.path.join(self.test_directory, "integrated_tool_panel.xml")
        self.app.config.integrated_tool_panel_config = itp_config
        self.__toolbox = None
        self.config_files = []

    @property
    def toolbox( self ):
        if self.__toolbox is None:
            self.__toolbox = SimplifiedToolBox( self )
        return self.__toolbox

    def __add_config( self, xml, name="tool_conf.xml" ):
        path = os.path.join( self.test_directory, "tool_conf.xml" )
        with open( path, "w" ) as f:
            f.write( xml )
        self.config_files.append( path )


class SimplifiedToolBox( ToolBox ):

    def __init__( self, test_case ):
        app = test_case.app
        # Handle app/config stuff needed by toolbox but not by tools.
        app.install_model = mapping.init( "sqlite:///:memory:", create_tables=True )
        app.job_config.get_tool_resource_parameters = lambda tool_id: None
        app.config.update_integrated_tool_panel = True
        config_files = test_case.config_files
        tool_root_dir = test_case.test_directory
        super( SimplifiedToolBox, self ).__init__(
            config_files,
            tool_root_dir,
            app,
        )
