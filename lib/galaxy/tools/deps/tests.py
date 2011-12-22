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
    for name, version, sub in [ ( "dep1", "1.0", "env.sh" ), ( "dep1", "2.0", "bin" ), ( "dep2", "1.0", None ) ]:
        if sub == "bin":
            p = os.path.join( base_path, name, version, "bin" ) 
        else:
            p = os.path.join( base_path, name, version ) 
        try:
            makedirs( p )
        except:
            pass
        if sub == "env.sh":
            touch( os.path.join( p, "env.sh" ) )

    dm = galaxy.tools.deps.DependencyManager( [ base_path ] )

    print dm.find_dep( "dep1", "1.0" )
    print dm.find_dep( "dep1", "2.0" )
