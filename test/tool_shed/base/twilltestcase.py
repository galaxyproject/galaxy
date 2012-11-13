from base.twilltestcase import *

class ShedTwillTestCase( TwillTestCase ):
    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = None
        self.host = os.environ.get( 'TOOL_SHED_TEST_HOST' )
        self.port = os.environ.get( 'TOOL_SHED_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', None )
        self.tool_shed_test_file = None
        self.shed_tools_dict = {}
        self.keepOutdir = os.environ.get( 'TOOL_SHED_TEST_SAVE', '' )
        if self.keepOutdir > '':
           try:
               os.makedirs( self.keepOutdir )
           except:
               pass
        self.home()
