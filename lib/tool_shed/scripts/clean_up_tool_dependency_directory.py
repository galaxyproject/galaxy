import argparse
import os
import sys
import shutil

def main( args ):
    if not os.path.exists( args.basepath ):
        print 'Tool dependency path %s does not exist.' % str( args.basepath )
        return 1
    if args.delete:
        print 'Deleting contents of tool dependency path %s.' % args.basepath
        for node in os.listdir( args.basepath ):
            path = os.path.join( args.basepath, node )
            if os.path.isdir( path ):
                try:
                    shutil.rmtree( path )
                    print 'Deleted directory %s and all its contents.' % path
                except Exception, e:
                    print 'Error deleting directory %s: %s' % ( path, str( e ) )
                    pass
            elif os.path.isfile( path ):
                try:
                    os.remove( path )
                    print 'Deleted file %s.' % path
                except Exception, e:
                    print 'Error deleting file %s: %s' % ( path, str( e ) )
                    pass
            elif os.path.islink( path ):
                print 'Deleting symlink %s with target %s.' % ( path, os.path.realpath( path ) )
                try:
                    os.remove( path )
                except Exception, e:
                    print 'Error deleting symlink %s: %s' % ( path, str( e ) )
                    pass
    else:
        print 'Tool dependency path %s contains the following files and directories:' % args.basepath
        for element in os.listdir( args.basepath ):
            print element
    return 0

if __name__ == '__main__':
    description = 'Clean out or list the contents of the provided tool dependency path. Remove if '
    description += 'the --delete command line argument is provided.'
    parser = argparse.ArgumentParser( description=description )
    parser.add_argument( '--delete',
                         dest='delete',
                         required=False,
                         action='store_true',
                         default=False,
                         help='Whether to delete all folders and files or list them on exit.' )
    parser.add_argument( '--basepath',
                         dest='basepath',
                         required=True,
                         action='store',
                         metavar='name',
                         help='The base path where tool dependencies are installed.' )
    args = parser.parse_args()
    sys.exit( main( args ) )
