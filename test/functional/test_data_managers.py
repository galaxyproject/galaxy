import new
import sys
import tempfile
import os.path
import shutil
from test_toolbox import ToolTestCase
from base.interactor import build_interactor, stage_data_in_history
import logging
log = logging.getLogger( __name__ )

data_managers = None

class DataManagerToolTestCase( ToolTestCase ):
    """Test case that runs Data Manager tests based on a `galaxy.tools.test.ToolTest`"""

    def do_it( self, testdef ):
        """
        Run through a tool test case.
        """
        shed_tool_id = self.shed_tool_id

        self._handle_test_def_errors( testdef )

        galaxy_interactor = self._galaxy_interactor( testdef )

        test_history = galaxy_interactor.new_history() #history where inputs will be put, if any

        stage_data_in_history( galaxy_interactor, testdef.test_data(), test_history, shed_tool_id )

        data_list = galaxy_interactor.run_tool( testdef, test_history ) #test_history will have inputs only, outputs are placed in the specialized data manager history
        
        #FIXME: Move history determination and switching into the interactor
        data_manager_history = None
        for assoc in reversed( test_history.user.data_manager_histories ):
            if not assoc.history.deleted:
                data_manager_history = assoc.history
                break
        self.switch_history( id=self.security.encode_id( data_manager_history.id ) )
        data_list = self.get_history_as_data_list()
        #end
        
        self.assertTrue( data_list )

        self._verify_outputs( testdef, data_manager_history, shed_tool_id, data_list, galaxy_interactor )
        
        self.switch_history( id=self.security.encode_id( test_history.id ) )

        galaxy_interactor.delete_history( test_history )

def build_tests( tmp_dir=None, testing_shed_tools=False, master_api_key=None, user_api_key=None ):
    """
    If the module level variable `data_managers` is set, generate `DataManagerToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    
    if data_managers is None:
        log.warning( 'data_managers was not set for Data Manager functional testing. Will not test.' )
        return

    # Push all the data_managers tests to module level
    G = globals()

    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestForDataManagerTool_' ):
            del G[ key ]

    #first we will loop through data table loc files and copy them to temporary location, then swap out filenames:
    for data_table_name, data_table in data_managers.app.tool_data_tables.get_tables().iteritems():
        for filename, value in list( data_table.filenames.items() ):
            new_filename = tempfile.NamedTemporaryFile( prefix=os.path.basename( filename ), dir=tmp_dir ).name
            try:
                shutil.copy( filename, new_filename )
            except IOError, e:
                log.warning( "Failed to copy '%s' to '%s', will create empty file at '%s': %s", filename, new_filename, new_filename, e )
                open( new_filename, 'wb' ).close()
            if 'filename' in value:
                value[ 'filename' ] = new_filename
            del data_table.filenames[ filename ] #remove filename:value pair
            data_table.filenames[ new_filename ] = value #add new value by 
    
    for i, ( data_manager_id, data_manager ) in enumerate( data_managers.data_managers.iteritems() ):
        tool = data_manager.tool
        if not tool:
            log.warning( "No Tool has been specified for Data Manager: %s", data_manager_id )
        tool_data_tables = data_manager.data_managers.app.tool_data_tables
        if tool.tests:
            ##fixme data_manager.tool_shed_repository_info_dict should be filled when is toolshed based
            shed_tool_id = None if not testing_shed_tools else tool.id
            # Create a new subclass of ToolTestCase, dynamically adding methods
            # named test_tool_XXX that run each test defined in the tool config.
            name = "TestForDataManagerTool_" + data_manager_id.replace( ' ', '_' )
            baseclasses = ( DataManagerToolTestCase, )
            namespace = dict()
            for j, testdef in enumerate( tool.tests ):
                def make_test_method( td ):
                    def test_tool( self ):
                        self.do_it( td )
                    return test_tool
                test_method = make_test_method( testdef )
                test_method.__doc__ = "%s ( %s ) > %s" % ( tool.name, tool.id, testdef.name )
                namespace[ 'test_tool_%06d' % j ] = test_method
                namespace[ 'shed_tool_id' ] = shed_tool_id
                namespace[ 'master_api_key' ] = master_api_key
                namespace[ 'user_api_key' ] = user_api_key
            # The new.classobj function returns a new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = new.classobj( name, baseclasses, namespace )
            G[ name ] = new_class_obj
