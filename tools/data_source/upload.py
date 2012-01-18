#!/usr/bin/env python
#Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools

import urllib, sys, os, gzip, tempfile, shutil, re, gzip, zipfile, codecs, binascii
from galaxy import eggs
# need to import model before sniff to resolve a circular import dependency
import galaxy.model
from galaxy.datatypes.checkers import *
from galaxy.datatypes import sniff
from galaxy.datatypes.binary import *
from galaxy.datatypes.images import Pdf
from galaxy.datatypes.registry import Registry
from galaxy import util
from galaxy.datatypes.util.image_util import *
from galaxy.util.json import *

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
    json_file.write( to_json_string( dict( type = 'dataset',
                                           ext = 'data',
                                           dataset_id = dataset.dataset_id,
                                           stderr = msg ) ) + "\n" )
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
        return dict([(k.encode('utf-8'), safe_dict(v)) for k,v in d.iteritems()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d
def check_bam( file_path ):
    return Bam().sniff( file_path )
def check_sff( file_path ):
    return Sff().sniff( file_path )
def check_pdf( file_path ):
    return Pdf().sniff( file_path )
def check_bigwig( file_path ):
    return BigWig().sniff( file_path )
def check_bigbed( file_path ):
    return BigBed().sniff( file_path )
def parse_outputs( args ):
    rval = {}
    for arg in args:
        id, files_path, path = arg.split( ':', 2 )
        rval[int( id )] = ( path, files_path )
    return rval
def add_file( dataset, registry, json_file, output_path ):
    data_type = None
    line_count = None
    converted_path = None
    stdout = None
    link_data_only = dataset.get( 'link_data_only', 'copy_files' )
    in_place = dataset.get( 'in_place', True )

    try:
        ext = dataset.file_type
    except AttributeError:
        file_err( 'Unable to process uploaded file, missing file_type parameter.', dataset, json_file )
        return

    if dataset.type == 'url':
        try:
            temp_name, dataset.is_multi_byte = sniff.stream_to_file( urllib.urlopen( dataset.path ), prefix='url_paste' )
        except Exception, e:
            file_err( 'Unable to fetch %s\n%s' % ( dataset.path, str( e ) ), dataset, json_file )
            return
        dataset.path = temp_name
    # See if we have an empty file
    if not os.path.exists( dataset.path ):
        file_err( 'Uploaded temporary file (%s) does not exist.' % dataset.path, dataset, json_file )
        return
    if not os.path.getsize( dataset.path ) > 0:
        file_err( 'The uploaded file is empty', dataset, json_file )
        return
    if not dataset.type == 'url':
        # Already set is_multi_byte above if type == 'url'
        try:
            dataset.is_multi_byte = util.is_multi_byte( codecs.open( dataset.path, 'r', 'utf-8' ).read( 100 ) )
        except UnicodeDecodeError, e:
            dataset.is_multi_byte = False
    # Is dataset an image?
    image = check_image( dataset.path )
    if image:
        if not PIL:
            image = None
        # get_image_ext() returns None if nor a supported Image type
        ext = get_image_ext( dataset.path, image )
        data_type = ext
    # Is dataset content multi-byte?
    elif dataset.is_multi_byte:
        data_type = 'multi-byte char'
        ext = sniff.guess_ext( dataset.path, is_multi_byte=True )
    # Is dataset content supported sniffable binary?
    elif check_bam( dataset.path ):
        ext = 'bam'
        data_type = 'bam'
    elif check_sff( dataset.path ):
        ext = 'sff'
        data_type = 'sff'
    elif check_pdf( dataset.path ):
        ext = 'pdf'
        data_type = 'pdf'
    elif check_bigwig( dataset.path ):
        ext = 'bigwig'
        data_type = 'bigwig'
    elif check_bigbed( dataset.path ):
        ext = 'bigbed'
        data_type = 'bigbed'
    if not data_type:
        # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress
        is_gzipped, is_valid = check_gzip( dataset.path )
        if is_gzipped and not is_valid:
            file_err( 'The gzipped uploaded file contains inappropriate content', dataset, json_file )
            return
        elif is_gzipped and is_valid:
            if link_data_only == 'copy_files':
                # We need to uncompress the temp_name file, but BAM files must remain compressed in the BGZF format
                CHUNK_SIZE = 2**20 # 1Mb   
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
                os.chmod(dataset.path, 0644)
            dataset.name = dataset.name.rstrip( '.gz' )
            data_type = 'gzip'
        if not data_type and bz2 is not None:
            # See if we have a bz2 file, much like gzip
            is_bzipped, is_valid = check_bz2( dataset.path )
            if is_bzipped and not is_valid:
                file_err( 'The gzipped uploaded file contains inappropriate content', dataset, json_file )
                return
            elif is_bzipped and is_valid:
                if link_data_only == 'copy_files':
                    # We need to uncompress the temp_name file
                    CHUNK_SIZE = 2**20 # 1Mb   
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
                    os.chmod(dataset.path, 0644)
                dataset.name = dataset.name.rstrip( '.bz2' )
                data_type = 'bz2'
        if not data_type:
            # See if we have a zip archive
            is_zipped = check_zip( dataset.path )
            if is_zipped:
                if link_data_only == 'copy_files':
                    CHUNK_SIZE = 2**20 # 1Mb
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
                        os.chmod(dataset.path, 0644)
                        dataset.name = uncompressed_name
                data_type = 'zip'
        if not data_type:
            if check_binary( dataset.path ):
                # We have a binary dataset, but it is not Bam, Sff or Pdf
                data_type = 'binary'
                #binary_ok = False
                parts = dataset.name.split( "." )
                if len( parts ) > 1:
                    ext = parts[1].strip().lower()
                    if ext not in unsniffable_binary_formats:
                        file_err( 'The uploaded binary file contains inappropriate content', dataset, json_file )
                        return
                    elif ext in unsniffable_binary_formats and dataset.file_type != ext:
                        err_msg = "You must manually set the 'File Format' to '%s' when uploading %s files." % ( ext.capitalize(), ext )
                        file_err( err_msg, dataset, json_file )
                        return
        if not data_type:
            # We must have a text file
            if check_html( dataset.path ):
                file_err( 'The uploaded file contains inappropriate HTML content', dataset, json_file )
                return
        if data_type != 'binary':
            if link_data_only == 'copy_files':
                if dataset.type in ( 'server_dir', 'path_paste' ) and data_type not in [ 'gzip', 'bz2', 'zip' ]:
                    in_place = False
                if dataset.space_to_tab:
                    line_count, converted_path = sniff.convert_newlines_sep2tabs( dataset.path, in_place=in_place )
                else:
                    line_count, converted_path = sniff.convert_newlines( dataset.path, in_place=in_place )
            if dataset.file_type == 'auto':
                ext = sniff.guess_ext( dataset.path, registry.sniff_order )
            else:
                ext = dataset.file_type
            data_type = ext
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
        shutil.move( dataset.path, output_path )
    # Write the job info
    stdout = stdout or 'uploaded %s file' % data_type
    info = dict( type = 'dataset',
                 dataset_id = dataset.dataset_id,
                 ext = ext,
                 stdout = stdout,
                 name = dataset.name,
                 line_count = line_count )
    json_file.write( to_json_string( info ) + "\n" )

    if link_data_only == 'copy_files' and datatype.dataset_content_needs_grooming( output_path ):
        # Groom the dataset content if necessary
        datatype.groom_dataset_content( output_path )

def add_composite_file( dataset, registry, json_file, output_path, files_path ):
        if dataset.composite_files:
            os.mkdir( files_path )
            for name, value in dataset.composite_files.iteritems():
                value = util.bunch.Bunch( **value )
                if dataset.composite_file_paths[ value.name ] is None and not value.optional:
                    file_err( 'A required composite data file was not provided (%s)' % name, dataset, json_file )
                    break
                elif dataset.composite_file_paths[value.name] is not None:
                    dp = dataset.composite_file_paths[value.name][ 'path' ]
                    isurl = dp.find('://') <> -1 # todo fixme
                    if isurl:
                       try:
                           temp_name, dataset.is_multi_byte = sniff.stream_to_file( urllib.urlopen( dp ), prefix='url_paste' )
                       except Exception, e:
                           file_err( 'Unable to fetch %s\n%s' % ( dp, str( e ) ), dataset, json_file )
                           return
                       dataset.path = temp_name
                       dp = temp_name
                    if not value.is_binary:
                        if dataset.composite_file_paths[ value.name ].get( 'space_to_tab', value.space_to_tab ):
                            sniff.convert_newlines_sep2tabs( dp )
                        else:
                            sniff.convert_newlines( dp )
                    shutil.move( dp, os.path.join( files_path, name ) )
        # Move the dataset to its "real" path
        shutil.move( dataset.primary_file, output_path )
        # Write the job info
        info = dict( type = 'dataset',
                     dataset_id = dataset.dataset_id,
                     stdout = 'uploaded %s file' % dataset.file_type )
        json_file.write( to_json_string( info ) + "\n" )

def __main__():

    if len( sys.argv ) < 4:
        print >>sys.stderr, 'usage: upload.py <root> <datatypes_conf> <json paramfile> <output spec> ...'
        sys.exit( 1 )

    output_paths = parse_outputs( sys.argv[4:] )
    json_file = open( 'galaxy.json', 'w' )

    registry = Registry()
    registry.load_datatypes( root_dir=sys.argv[1], config=sys.argv[2] )

    for line in open( sys.argv[3], 'r' ):
        dataset = from_json_string( line )
        dataset = util.bunch.Bunch( **safe_dict( dataset ) )
        try:
            output_path = output_paths[int( dataset.dataset_id )][0]
        except:
            print >>sys.stderr, 'Output path for dataset %s not found on command line' % dataset.dataset_id
            sys.exit( 1 )
        if dataset.type == 'composite':
            files_path = output_paths[int( dataset.dataset_id )][1]
            add_composite_file( dataset, registry, json_file, output_path, files_path )
        else:
            add_file( dataset, registry, json_file, output_path )

    # clean up paramfile
    # TODO: this will not work when running as the actual user unless the
    # parent directory is writable by the user.
    try:
        os.remove( sys.argv[3] )
    except:
        pass

if __name__ == '__main__':
    __main__()
