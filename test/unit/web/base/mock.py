"""
"""
import tempfile
import os
import shutil

class MockDir( object ):

    def __init__( self, structure_dict, where=None ):
        self.structure_dict = structure_dict
        self.create_root( structure_dict, where )

    def create_root( self, structure_dict, where=None ):
        self.root_path = tempfile.mkdtemp( dir=where )
        #print 'created root:', self.root_path
        self.create_structure( self.root_path, structure_dict )

    def create_structure( self, current_path, structure_dict ):
        for k, v in structure_dict.items():
            # if value is string, create a file in the current path and write v as file contents
            if isinstance( v, str ):
                self.create_file( os.path.join( current_path, k ), v )
            # if it's a dict, create a dir here named k and recurse into it
            if isinstance( v, dict ):
                subdir_path = os.path.join( current_path, k )
                #print 'subdir:', subdir_path
                os.mkdir( subdir_path )
                self.create_structure( subdir_path, v )

    def create_file( self, path, contents ):
        #print 'file:', path
        with open( path, 'w' ) as newfile:
            newfile.write( contents )

    def remove( self ):
        #print 'removing:', self.root_path
        shutil.rmtree( self.root_path )


class MockAppConfig( object ):
    def __init__( self, root ):
        self.root = root

class MockApp( object ):
    def __init__( self, root ):
        self.config = MockAppConfig( root )

class MockTrans( object ):
    def fill_template( self, filename, template_lookup=None, **kwargs ):
        template = template_lookup.get_template( filename )
        template.output_encoding = 'utf-8'
        return template.render( **kwargs )

if __name__ == '__main__':
    td = MockDir({
        'file1' : 'Hello\nthere,\t...you',
        'dir1'  : {
            'file2' : 'Blerbler',
        }
    })
    td.remove()
