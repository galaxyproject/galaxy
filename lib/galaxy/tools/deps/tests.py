import tempfile
import os.path
from os import makedirs, mkdir
import galaxy.tools.deps

def touch( fname, data=None ):
    f = open( fname, 'w' )
    if data:
        f.write( data )
    f.close()

def test():

    # Setup directories
    base_path = tempfile.mkdtemp()
    # mkdir( base_path )
    for name, version in [ ( "dep1", "1.0" ), ( "dep1", "2.0" ), ( "dep2", "1.0" ) ]:
        p = os.path.join( base_path, name, version ) 
        try:
            makedirs( p )
        except:
            pass
        touch( os.path.join( p, "env.sh" ) )

    dm = galaxy.tools.deps.DependencyManager( [ base_path ] )

    print dm.find_dep( "dep1", "2.0" )

    




