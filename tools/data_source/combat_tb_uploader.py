#!/usr/bin/env python
# Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools
from __future__ import print_function

import cProfile
import logging
import codecs
import gzip
import os
import shutil
import sys
import tempfile
import zipfile
import multiprocessing
from json import dumps, loads

from six.moves.urllib.request import urlopen

sys.path.insert(0, "/home/zipho/workspace/sanbi/dev/galaxy/lib")

from galaxy import util
from galaxy.datatypes import sniff
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.util.image_util import get_image_ext
from galaxy.util import multi_byte
from galaxy.util.checkers import check_binary, check_bz2, check_gzip, check_html, check_image, check_zip

log = logging.getLogger( __name__ )

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except:
        PIL = None

try:
    import bz2
except:
    bz2 = None

assert sys.version_info[:2] >= ( 2, 4 )


def stop_err( msg, ret=1 ):
    sys.stderr.write( msg )
    sys.exit( ret )


def file_err( msg, dataset, json_file ):
    json_file.write( dumps( dict( type='dataset',
                                  ext='data',
                                  dataset_id=dataset.dataset_id,
                                  stderr=msg ) ) + "\n" )
    # never remove a server-side upload
    if dataset.type in ( 'server_dir', 'path_paste' ):
        return
    try:
        os.remove( dataset.path )
    except:
        pass


def safe_dict(d):
    """
    Recursively clone json structure with UTF-8 dictionary keys
    http://mellowmachines.com/blog/2009/06/exploding-dictionary-with-unicode-keys-as-python-arguments/
    """
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v)) for k, v in d.items()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d


def parse_outputs( args ):
    rval = {}
    for arg in args:
        id, files_path, path = arg.split( ':', 2 )
        rval[int( id )] = ( path, files_path )
    return rval

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats(sort='time')
    return profiled_func

#@do_cprofile
def add_file( dataset, registry, json_file, output_path ):
    data_type = None
    line_count = None
    converted_path = None
    stdout = None
    link_data_only = dataset.get( 'link_data_only', 'copy_files' )
    in_place = dataset.get( 'in_place', True )
    purge_source = dataset.get( 'purge_source', True )

    #----------------- The following checks the sanity of the uploaded dataset -----------------#
    # Looking for the file type on the file
    try:
        ext = dataset.file_type
    except AttributeError:
        file_err( 'Unable to process uploaded file, missing file_type parameter.', dataset, json_file )
        return

    # See if we have an empty file
    if not os.path.exists( dataset.path ):
        file_err( 'Uploaded temporary file (%s) does not exist.' % dataset.path, dataset, json_file )
        return
    if not os.path.getsize( dataset.path ) > 0:
        file_err( 'The uploaded file is empty', dataset, json_file )
        return

    #---------------- The following attempts to set the dataset ext and datatype ----------------------------#
    # this attempts to set the multi_byte of the dataset
    try:
        dataset.is_multi_byte = multi_byte.is_multi_byte( codecs.open( dataset.path, 'r', 'utf-8' ).read( 100 ) )
    except UnicodeDecodeError as e:
        dataset.is_multi_byte = False

    # Is dataset content multi-byte?
    if dataset.is_multi_byte:
        data_type = 'multi-byte char'
        ext = sniff.guess_ext( dataset.path, registry.sniff_order, is_multi_byte=True )
    # Is dataset content supported sniffable binary?
    else:
        # FIXME: This ignores the declared sniff order in datatype_conf.xml resulting in improper behavior
        type_info = Binary.is_sniffable_binary( dataset.path )
        if type_info:
            data_type = type_info[0]
            ext = type_info[1]

    #------------------ The following attempts to set the dataset ext and datatype, if the above failed -----#
    if not data_type:
        root_datatype = registry.get_datatype_by_extension( dataset.file_type )
        if getattr( root_datatype, 'compressed', False ):
            data_type = 'compressed archive'
            ext = dataset.file_type
        else:
            ##### ----------- GZIP --------------#####
            # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress
            is_gzipped, is_valid = check_gzip( dataset.path )
            if is_gzipped and not is_valid:
                file_err( 'The gzipped uploaded file contains inappropriate content', dataset, json_file )
                return
            elif is_gzipped and is_valid:
                if link_data_only == 'copy_files':
                    # We need to uncompress the temp_name file, but BAM files must remain compressed in the BGZF format
                    CHUNK_SIZE = 2 ** 20  # 1Mb
                    fd, uncompressed = tempfile.mkstemp( prefix='data_id_%s_upload_gunzip_' % dataset.dataset_id, dir=os.path.dirname( output_path ), text=False )
                    gzipped_file = gzip.GzipFile( dataset.path, 'rb' )
                    while 1:
                        try:
                            chunk = gzipped_file.read( CHUNK_SIZE )
                        except IOError:
                            os.close( fd )
                            os.remove( uncompressed )
                            file_err( 'Problem decompressing gzipped data', dataset, json_file )
                            return
                        if not chunk:
                            break
                        os.write( fd, chunk )
                    os.close( fd )
                    gzipped_file.close()
                    # Replace the gzipped file with the decompressed file if it's safe to do so
                    if dataset.type in ( 'server_dir', 'path_paste' ) or not in_place:
                        dataset.path = uncompressed
                    else:
                        shutil.move( uncompressed, dataset.path )
                    os.chmod(dataset.path, 0o644)
                dataset.name = dataset.name.rstrip( '.gz' )
                data_type = 'gzip'

            ##### ----------- BZ2 --------------#####
            if not data_type and bz2 is not None:
                # See if we have a bz2 file, much like gzip
                is_bzipped, is_valid = check_bz2( dataset.path )
                if is_bzipped and not is_valid:
                    file_err( 'The gzipped uploaded file contains inappropriate content', dataset, json_file )
                    return
                elif is_bzipped and is_valid:
                    if link_data_only == 'copy_files':
                        # We need to uncompress the temp_name file
                        CHUNK_SIZE = 2 ** 20  # 1Mb
                        fd, uncompressed = tempfile.mkstemp( prefix='data_id_%s_upload_bunzip2_' % dataset.dataset_id, dir=os.path.dirname( output_path ), text=False )
                        bzipped_file = bz2.BZ2File( dataset.path, 'rb' )
                        while 1:
                            try:
                                chunk = bzipped_file.read( CHUNK_SIZE )
                            except IOError:
                                os.close( fd )
                                os.remove( uncompressed )
                                file_err( 'Problem decompressing bz2 compressed data', dataset, json_file )
                                return
                            if not chunk:
                                break
                            os.write( fd, chunk )
                        os.close( fd )
                        bzipped_file.close()
                        # Replace the bzipped file with the decompressed file if it's safe to do so
                        if dataset.type in ( 'server_dir', 'path_paste' ) or not in_place:
                            dataset.path = uncompressed
                        else:
                            shutil.move( uncompressed, dataset.path )
                        os.chmod(dataset.path, 0o644)
                    dataset.name = dataset.name.rstrip( '.bz2' )
                    data_type = 'bz2'
            ##### ----------- ZIP --------------#####
            if not data_type:
                # See if we have a zip archive
                is_zipped = check_zip( dataset.path )
                if is_zipped:
                    if link_data_only == 'copy_files':
                        CHUNK_SIZE = 2 ** 20  # 1Mb
                        uncompressed = None
                        uncompressed_name = None
                        unzipped = False
                        z = zipfile.ZipFile( dataset.path )
                        for name in z.namelist():
                            if name.endswith('/'):
                                continue
                            if unzipped:
                                stdout = 'ZIP file contained more than one file, only the first file was added to Galaxy.'
                                break
                            fd, uncompressed = tempfile.mkstemp( prefix='data_id_%s_upload_zip_' % dataset.dataset_id, dir=os.path.dirname( output_path ), text=False )
                            if sys.version_info[:2] >= ( 2, 6 ):
                                zipped_file = z.open( name )
                                while 1:
                                    try:
                                        chunk = zipped_file.read( CHUNK_SIZE )
                                    except IOError:
                                        os.close( fd )
                                        os.remove( uncompressed )
                                        file_err( 'Problem decompressing zipped data', dataset, json_file )
                                        return
                                    if not chunk:
                                        break
                                    os.write( fd, chunk )
                                os.close( fd )
                                zipped_file.close()
                                uncompressed_name = name
                                unzipped = True
                            else:
                                # python < 2.5 doesn't have a way to read members in chunks(!)
                                try:
                                    outfile = open( uncompressed, 'wb' )
                                    outfile.write( z.read( name ) )
                                    outfile.close()
                                    uncompressed_name = name
                                    unzipped = True
                                except IOError:
                                    os.close( fd )
                                    os.remove( uncompressed )
                                    file_err( 'Problem decompressing zipped data', dataset, json_file )
                                    return
                        z.close()
                        # Replace the zipped file with the decompressed file if it's safe to do so
                        if uncompressed is not None:
                            if dataset.type in ( 'server_dir', 'path_paste' ) or not in_place:
                                dataset.path = uncompressed
                            else:
                                shutil.move( uncompressed, dataset.path )
                            os.chmod(dataset.path, 0o644)
                            dataset.name = uncompressed_name
                    data_type = 'zip'

            ##### ----------- BINARY --------------#####
            if not data_type:
                # TODO refactor this logic.  check_binary isn't guaranteed to be
                # correct since it only looks at whether the first 100 chars are
                # printable or not.  If someone specifies a known unsniffable
                # binary datatype and check_binary fails, the file gets mangled.
                if check_binary( dataset.path ) or Binary.is_ext_unsniffable(dataset.file_type):
                    # We have a binary dataset, but it is not Bam, Sff or Pdf
                    data_type = 'binary'
                    # binary_ok = False
                    parts = dataset.name.split( "." )
                    if len( parts ) > 1:
                        ext = parts[-1].strip().lower()
                        if not Binary.is_ext_unsniffable(ext):
                            file_err( 'The uploaded binary file contains inappropriate content', dataset, json_file )
                            return
                        elif Binary.is_ext_unsniffable(ext) and dataset.file_type != ext:
                            err_msg = "You must manually set the 'File Format' to '%s' when uploading %s files." % ( ext.capitalize(), ext )
                            file_err( err_msg, dataset, json_file )
                            return
            ##### ----------- HTML --------------#####
            if not data_type:
                # We must have a text file
                if check_html( dataset.path ):
                    file_err( 'The uploaded file contains inappropriate HTML content', dataset, json_file )
                    return

            #-------- This is when datatype is known -----------------------------------------------------------------#
            if data_type != 'binary':
                if dataset.file_type == 'auto':
                    ext = sniff.guess_ext( dataset.path, registry.sniff_order )
                else:
                    ext = dataset.file_type
                data_type = ext

    #####-------------------- JOB PART ---------------------------#####
    # Save job info for the framework
    if ext == 'auto' and dataset.ext:
        ext = dataset.ext
    if ext == 'auto':
        ext = 'data'
    datatype = registry.get_datatype_by_extension( ext )
    if dataset.type in ( 'server_dir', 'path_paste' ) and link_data_only == 'link_to_files':
        # Never alter a file that will not be copied to Galaxy's local file store.
        if datatype.dataset_content_needs_grooming( dataset.path ):
            err_msg = 'The uploaded files need grooming, so change your <b>Copy data into Galaxy?</b> selection to be ' + \
                '<b>Copy files into Galaxy</b> instead of <b>Link to files without copying into Galaxy</b> so grooming can be performed.'
            file_err( err_msg, dataset, json_file )
            return
    if link_data_only == 'copy_files' and dataset.type in ( 'server_dir', 'path_paste' ) and data_type not in [ 'gzip', 'bz2', 'zip' ]:
        # Move the dataset to its "real" path
        if converted_path is not None:
            shutil.copy( converted_path, output_path )
            try:
                os.remove( converted_path )
            except:
                pass
        else:
            # This should not happen, but it's here just in case
            shutil.copy( dataset.path, output_path )
    elif link_data_only == 'copy_files':
        if purge_source:
            shutil.move( dataset.path, output_path )
        else:
            shutil.copy( dataset.path, output_path )
    # Write the job info
    stdout = stdout or 'uploaded %s file' % data_type
    info = dict( type='dataset',
                 dataset_id=dataset.dataset_id,
                 ext=ext,
                 stdout=stdout,
                 name=dataset.name,
                 line_count=line_count )
    if dataset.get('uuid', None) is not None:
        info['uuid'] = dataset.get('uuid')
    json_file.write( dumps( info ) + "\n" )

    if link_data_only == 'copy_files' and datatype.dataset_content_needs_grooming( output_path ):
        # Groom the dataset content if necessary
        datatype.groom_dataset_content( output_path )

def output_adjacent_tmpdir( output_path ):
    """ For temp files that will ultimately be moved to output_path anyway
    just create the file directly in output_path's directory so shutil.move
    will work optimially.
    """
    return os.path.dirname( output_path )

class uploadFileObject():
    def __init__(self, params):
        self.dataset, self.root_dir, self.config, self.json_file, self.output_path = params

def upload_worker(obj):
    dataset, root_dir, config, json_file, output_path = obj.dataset, obj.root_dir, obj.config, obj.json_file, obj.output_path
    registry = Registry()
    registry.load_datatypes(root_dir=root_dir, config=config)
    add_file(dataset, registry, open( 'galaxy.json', 'w' ), output_path)

def __main__():

    if len( sys.argv ) < 4:
        print('usage: combat_tb_uploader.py <root> <datatypes_conf> <json paramfile> <output spec> ...', file=sys.stderr)
        sys.exit( 1 )

    output_paths = parse_outputs( sys.argv[4:] )
    json_file = open( 'galaxy.json', 'w' )

    registry = Registry()
    registry.load_datatypes(root_dir=sys.argv[1], config=sys.argv[2])

    for line in open( sys.argv[3], 'r' ):
        dataset = loads( line )
        dataset = util.bunch.Bunch(**safe_dict(dataset))
        try:
            output_path = output_paths[int(dataset.dataset_id)][0]
        except:
            print('Output path for dataset %s not found on command line' % dataset.dataset_id, file=sys.stderr)
            sys.exit( 1 )
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        objList = [uploadFileObject((dataset, sys.argv[1], sys.argv[2], json_file, output_path))]
        pool.map(upload_worker, objList)

    # clean up paramfile
    # TODO: this will not work when running as the actual user unless the
    # parent directory is writable by the user.
    try:
        os.remove( sys.argv[3] )
    except:
        pass

if __name__ == '__main__':
    __main__()
