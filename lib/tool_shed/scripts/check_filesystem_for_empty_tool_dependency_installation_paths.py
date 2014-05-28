import argparse
import os
import sys
import shutil

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from tool_shed.util.basic_util import INSTALLATION_LOG
    
def main( args ):
    empty_installation_paths = []
    if not os.path.exists( args.basepath ):
        print 'Tool dependency path %s does not exist.' % str( args.basepath )
        return 1
    print 'Checking path %s for empty tool dependency installation directories.' % args.basepath
    for root, dirs, files in os.walk( args.basepath ):
        path_parts = root.replace( args.basepath, '' ).lstrip( '/' ).split( os.sep )
        # Skip certain special directories.
        if '__virtualenv_src' in dirs:
            dirs.remove( '__virtualenv_src' )
        if 'environment_settings' in dirs:
            dirs.remove( 'environment_settings' )
        # Do not process the current path if it does not match the pattern 
        # <name>/<version>/<owner>/<repository>/<changeset>.
        if len( path_parts ) != 5:
            continue
        # We have a tool dependency installation path.
        no_dirs = False
        no_files = False
        if len( dirs ) == 0:
            no_dirs = True
        if len( files ) == 0 or len( files ) == 1 and INSTALLATION_LOG in files:
            no_files = True
        if no_files and no_dirs and root not in empty_installation_paths:
            empty_installation_paths.append( root )
    if len( empty_installation_paths ) > 0:
        print 'The following %d tool dependency installation directories were found to be empty or contain only the file %s.' % \
            ( len( empty_installation_paths ), INSTALLATION_LOG )
        if args.delete:
            for path in empty_installation_paths:
                if os.path.exists( path ):
                    shutil.rmtree( path )
                    print 'Deleted %s.' % path
        else:
            for empty_installation_path in empty_installation_paths:
                print empty_installation_path
    else:
        print 'No empty tool dependency installation directories found.'
    return 0

if __name__ == '__main__':
    description = 'Determine if there are any tool dependency installation paths that should be removed. Remove them if '
    description += 'the --delete command line argument is provided.'
    parser = argparse.ArgumentParser( description=description )
    parser.add_argument( '--delete',
                         dest='delete',
                         required=False,
                         action='store_true',
                         default=False,
                         help='Whether to delete empty folders or list them on exit.' )
    parser.add_argument( '--basepath',
                         dest='basepath',
                         required=True,
                         action='store',
                         metavar='name',
                         help='The base path where tool dependencies are installed.' )
    args = parser.parse_args()
    sys.exit( main( args ) )
