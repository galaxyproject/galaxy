import argparse
import os
import sys
import shutil

def main( args ):
    if not os.path.exists( args.tool_dependency_dir ):
        print 'Tool dependency base path %s does not exist, creating.' % str( args.tool_dependency_dir )
        os.mkdir( args.tool_dependency_dir )
        return 0
    else:
        for content in os.listdir( args.tool_dependency_dir ):
            print 'Deleting directory %s from %s.' % ( content, args.tool_dependency_dir )
            full_path = os.path.join( args.tool_dependency_dir, content )
            if os.path.isdir( full_path ):
                shutil.rmtree( full_path )
            else:
                os.remove( full_path )

if __name__ == '__main__':
    description = 'Clean out the configured tool dependency path, creating it if it does not exist.'
    parser = argparse.ArgumentParser( description=description )
    parser.add_argument( '--tool_dependency_dir',
                         dest='tool_dependency_dir',
                         required=True,
                         action='store',
                         metavar='name',
                         help='The base path where tool dependencies will be installed.' )
    args = parser.parse_args()
    sys.exit( main( args ) )
