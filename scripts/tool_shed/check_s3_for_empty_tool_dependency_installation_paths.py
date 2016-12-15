import argparse
import os
import sys

sys.path.insert(1, os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir, 'lib' ) )

import boto

from galaxy.util import asbool
from tool_shed.util.basic_util import INSTALLATION_LOG


class BucketList( object ):

    def __init__( self, amazon_id, amazon_secret, bucket ):
        # Connect to S3 using the provided Amazon access key and secret identifier.
        self.s3 = boto.connect_s3( amazon_id, amazon_secret )
        self.bucket_name = bucket
        # Connect to S3 using the received bucket name.
        self.bucket = boto.s3.bucket.Bucket( self.s3, bucket )
        self.install_dirs = self.get_tool_dependency_install_paths()
        self.empty_installation_paths = self.check_for_empty_tool_dependency_installation_paths()

    def display_empty_installation_paths( self ):
        for empty_installation_path in self.empty_installation_paths:
            print empty_installation_path

    def delete_empty_installation_paths( self ):
        print 'Deleting empty installation paths.'
        for empty_installation_path in self.empty_installation_paths:
            # Get all keys in the S3 bucket that start with the installation path, and delete each one.
            for path_to_delete in self.bucket.list( prefix=empty_installation_path ):
                self.bucket.delete_key( path_to_delete.key )
                print 'Deleted empty path %s' % str( empty_installation_path )

    def get_tool_dependency_install_paths( self ):
        found_paths = []
        for item in self.bucket.list():
            name = str( item.name )
            # Skip environment_settings and __virtualenv_src, since these directories do not contain package tool dependencies.
            if name.startswith( 'environment_settings' ) or name.startswith( '__virtualenv_src' ):
                continue
            paths = name.rstrip('/').split( '/' )
            # Paths are in the format name/version/owner/repository/changeset_revision. If the changeset revision is
            # present, we need to check the contents of that path. If not, then the tool dependency was completely
            # uninstalled.
            if len( paths ) >= 5:
                td_install_dir = '/'.join( paths[ :5 ] ) + '/'
                if td_install_dir not in found_paths:
                    found_paths.append( name )
        return found_paths

    def check_for_empty_tool_dependency_installation_paths( self ):
        empty_directories = []
        for item in self.install_dirs:
            # Get all entries under the path for this tool dependency.
            contents = self.bucket.list( prefix=item )
            tool_dependency_path_contents = []
            # Find out if there are two or less items in the path. The first entry will be the installation path itself.
            # If only one other item exists, and the full path ends with the installation log, this is an incorrectly installed
            # tool dependency.
            for item in contents:
                tool_dependency_path_contents.append( item )
                # If there are more than two items in the path, we cannot safely assume that the dependency failed to
                # install correctly.
                if len( tool_dependency_path_contents ) > 2:
                    break
            # If the root directory is the only entry in the path, we have an empty tool dependency installation path.
            if len( tool_dependency_path_contents ) == 1:
                empty_directories.append( tool_dependency_path_contents[ 0 ] )
            # Otherwise, if the only other entry is the installation log, we have an installation path that should be deleted.
            # This would not be the case in a Galaxy instance, since the Galaxy admin will need to verify the contents of
            # the installation path in order to determine which action should be taken.
            elif len( tool_dependency_path_contents ) == 2 and \
                    tool_dependency_path_contents[1].name.endswith( INSTALLATION_LOG ):
                empty_directories.append( tool_dependency_path_contents[ 0 ] )
        return [ item.name for item in empty_directories ]


def main( args ):
    '''
    Amazon credentials can be provided in one of three ways:
    1. By specifying them on the command line with the --id and --secret arguments.
    2. By specifying a path to a file that contains the credentials in the form ACCESS_KEY:SECRET_KEY
       using the --s3passwd argument.
    3. By specifying the above path in the 's3passwd' environment variable.
    Each listed option will override the ones below it, if present.
    '''
    if None in [ args.id, args.secret ]:
        if args.s3passwd is None:
            args.s3passwd = os.environ.get( 's3passwd', None )
        if args.s3passwd is not None and os.path.exists( args.s3passwd ):
            awsid, secret = open( args.s3passwd, 'r' ).read().rstrip( '\n' ).split( ':' )
        else:
            print 'Amazon ID and secret not provided, and no s3passwd file found.'
            return 1
    else:
        awsid = args.id
        secret = args.secret
    dependency_cleaner = BucketList( awsid, secret, args.bucket )
    if len( dependency_cleaner.empty_installation_paths ) == 0:
        print 'No empty installation paths found, exiting.'
        return 0
    print 'The following %d tool dependency installation paths were found to be empty or contain only the file %s.' % \
        ( len( dependency_cleaner.empty_installation_paths ), INSTALLATION_LOG )
    if asbool( args.delete ):
        dependency_cleaner.delete_empty_installation_paths()
    else:
        for empty_installation_path in dependency_cleaner.empty_installation_paths:
            print empty_installation_path
    return 0


if __name__ == '__main__':
    description = 'Determine if there are any tool dependency installation paths that should be removed. Remove them if '
    description += 'the --delete command line argument is provided with a true value.'
    parser = argparse.ArgumentParser( description=description )
    parser.add_argument( '--delete',
                         dest='delete',
                         required=True,
                         action='store',
                         default=False,
                         type=asbool,
                         help='Whether to delete empty folders or list them on exit.' )
    parser.add_argument( '--bucket',
                         dest='bucket',
                         required=True,
                         action='store',
                         metavar='name',
                         help='The S3 bucket where tool dependencies are installed.' )
    parser.add_argument( '--id',
                         dest='id',
                         required=False,
                         action='store',
                         default=None,
                         metavar='ACCESS_KEY',
                         help='The identifier for an amazon account that has read access to the bucket.' )
    parser.add_argument( '--secret',
                         dest='secret',
                         required=False,
                         action='store',
                         default=None,
                         metavar='SECRET_KEY',
                         help='The secret key for an amazon account that has upload/delete access to the bucket.' )
    parser.add_argument( '--s3passwd',
                         dest='s3passwd',
                         required=False,
                         action='store',
                         default=None,
                         metavar='path/file',
                         help='The path to a file containing Amazon access credentials, in the format KEY:SECRET.' )
    args = parser.parse_args()
    sys.exit( main( args ) )
