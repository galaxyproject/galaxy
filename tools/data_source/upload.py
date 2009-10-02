#!/usr/bin/env python
#Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools

import urllib, sys, os, gzip, tempfile, shutil, re, gzip, zipfile
from galaxy import eggs
# need to import model before sniff to resolve a circular import dependency
import galaxy.model
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.json import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg, ret=1 ):
    sys.stderr.write( msg )
    sys.exit( ret )

def file_err( msg, dataset, json_file ):
    json_file.write( to_json_string( dict( type = 'dataset',
                                           ext = 'data',
                                           dataset_id = dataset.dataset_id,
                                           stderr = msg ) ) + "\n" )
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

def check_html( temp_name, chunk=None ):
    if chunk is None:
        temp = open(temp_name, "U")
    else:
        temp = chunk
    regexp1 = re.compile( "<A\s+[^>]*HREF[^>]+>", re.I )
    regexp2 = re.compile( "<IFRAME[^>]*>", re.I )
    regexp3 = re.compile( "<FRAMESET[^>]*>", re.I )
    regexp4 = re.compile( "<META[^>]*>", re.I )
    regexp5 = re.compile( "<SCRIPT[^>]*>", re.I )
    lineno = 0
    for line in temp:
        lineno += 1
        matches = regexp1.search( line ) or regexp2.search( line ) or regexp3.search( line ) or regexp4.search( line ) or regexp5.search( line )
        if matches:
            if chunk is None:
                temp.close()
            return True
        if lineno > 100:
            break
    if chunk is None:
        temp.close()
    return False

def check_binary( temp_name, chunk=None ):
    if chunk is None:
        temp = open( temp_name, "U" )
    else:
        temp = chunk
    lineno = 0
    for line in temp:
        lineno += 1
        line = line.strip()
        if line:
            for char in line:
                if ord( char ) > 128:
                    if chunk is None:
                        temp.close()
                    return True
        if lineno > 10:
            break
    if chunk is None:
        temp.close()
    return False

def check_gzip( temp_name ):
    temp = open( temp_name, "U" )
    magic_check = temp.read( 2 )
    temp.close()
    if magic_check != util.gzip_magic:
        return ( False, False )
    CHUNK_SIZE = 2**15 # 32Kb
    gzipped_file = gzip.GzipFile( temp_name )
    chunk = gzipped_file.read( CHUNK_SIZE )
    gzipped_file.close()
    if check_html( temp_name, chunk=chunk ) or check_binary( temp_name, chunk=chunk ):
        return( True, False )
    return ( True, True )

def check_zip( temp_name ):
    if not zipfile.is_zipfile( temp_name ):
        return ( False, False, None )
    zip_file = zipfile.ZipFile( temp_name, "r" )
    # Make sure the archive consists of valid files.  The current rules are:
    # 1. Archives can only include .ab1, .scf or .txt files
    # 2. All file extensions within an archive must be the same
    name = zip_file.namelist()[0]
    test_ext = name.split( "." )[1].strip().lower()
    if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
        return ( True, False, test_ext )
    for name in zip_file.namelist():
        ext = name.split( "." )[1].strip().lower()
        if ext != test_ext:
            return ( True, False, test_ext )
    return ( True, True, test_ext )

def parse_outputs( args ):
    rval = {}
    for arg in args:
        id, path = arg.split( ':', 1 )
        rval[int( id )] = path
    return rval

def add_file( dataset, json_file, output_path ):
    data_type = None
    line_count = None

    if dataset.type == 'url':
        try:
            temp_name, is_multi_byte = sniff.stream_to_file( urllib.urlopen( dataset.path ), prefix='url_paste' )
        except Exception, e:
            file_err( 'Unable to fetch %s\n%s' % ( dataset.path, str( e ) ), dataset, json_file )
            return
        dataset.path = temp_name
        dataset.is_multi_byte = is_multi_byte

    # See if we have an empty file
    if not os.path.exists( dataset.path ):
        file_err( 'Uploaded temporary file (%s) does not exist.' % dataset.path, dataset, json_file )
        return
    if not os.path.getsize( dataset.path ) > 0:
        file_err( 'The uploaded file is empty', dataset, json_file )
        return
    if 'is_multi_byte' not in dir( dataset ):
        dataset.is_multi_byte = util.is_multi_byte( open( dataset.path, 'r' ).read( 1024 ) )
    if dataset.is_multi_byte:
        ext = sniff.guess_ext( dataset.path, is_multi_byte=True )
        data_type = ext
    else:
        # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress
        is_gzipped, is_valid = check_gzip( dataset.path )
        if is_gzipped and not is_valid:
            file_err( 'The uploaded file contains inappropriate content', dataset, json_file )
            return
        elif is_gzipped and is_valid:
            # We need to uncompress the temp_name file
            CHUNK_SIZE = 2**20 # 1Mb   
            fd, uncompressed = tempfile.mkstemp( prefix='data_id_%s_upload_gunzip_' % dataset.dataset_id, dir=os.path.dirname( dataset.path ) )
            gzipped_file = gzip.GzipFile( dataset.path )
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
            # Replace the gzipped file with the decompressed file
            shutil.move( uncompressed, dataset.path )
            dataset.name = dataset.name.rstrip( '.gz' )
            data_type = 'gzip'
        if not data_type:
            # See if we have a zip archive
            is_zipped, is_valid, test_ext = check_zip( dataset.path )
            if is_zipped and not is_valid:
                file_err( 'The uploaded file contains inappropriate content', dataset, json_file )
                return
            elif is_zipped and is_valid:
                # Currently, we force specific tools to handle this case.  We also require the user
                # to manually set the incoming file_type
                if ( test_ext == 'ab1' or test_ext == 'scf' ) and dataset.file_type != 'binseq.zip':
                    file_err( "Invalid 'File Format' for archive consisting of binary files - use 'Binseq.zip'", dataset, json_file )
                    return
                elif test_ext == 'txt' and dataset.file_type != 'txtseq.zip':
                    file_err( "Invalid 'File Format' for archive consisting of text files - use 'Txtseq.zip'", dataset, json_file )
                    return
                if not ( dataset.file_type == 'binseq.zip' or dataset.file_type == 'txtseq.zip' ):
                    file_err( "You must manually set the 'File Format' to either 'Binseq.zip' or 'Txtseq.zip' when uploading zip files", dataset, json_file )
                    return
                data_type = 'zip'
                ext = dataset.file_type
        if not data_type:
            if check_binary( dataset.path ):
                if dataset.is_binary is not None:
                    data_type = 'binary'
                    ext = dataset.file_type
                else:
                    parts = dataset.name.split( "." )
                    if len( parts ) > 1:
                        ext = parts[1].strip().lower()
                        if not( ext == 'ab1' or ext == 'scf' ):
                            file_err( 'The uploaded file contains inappropriate content', dataset, json_file )
                            return
                        if ext == 'ab1' and dataset.file_type != 'ab1':
                            file_err( "You must manually set the 'File Format' to 'Ab1' when uploading ab1 files.", dataset, json_file )
                            return
                        elif ext == 'scf' and dataset.file_type != 'scf':
                            file_err( "You must manually set the 'File Format' to 'Scf' when uploading scf files.", dataset, json_file )
                            return
                    else:
                        ext = 'binary'
                    data_type = 'binary'
        if not data_type:
            # We must have a text file
            if check_html( dataset.path ):
                file_err( 'The uploaded file contains inappropriate content', dataset, json_file )
                return
        if data_type != 'binary' and data_type != 'zip':
            if dataset.space_to_tab:
                line_count = sniff.convert_newlines_sep2tabs( dataset.path )
            else:
                line_count = sniff.convert_newlines( dataset.path )
            if dataset.file_type == 'auto':
                ext = sniff.guess_ext( dataset.path )
            else:
                ext = dataset.file_type
            data_type = ext
    # Save job info for the framework
    if ext == 'auto' and dataset.ext:
        ext = dataset.ext
    if ext == 'auto':
        ext = 'data'
    # Move the dataset to its "real" path
    if dataset.get( 'link_data_only', False ):
        pass # data will remain in place
    elif dataset.type in ( 'server_dir', 'path_paste' ):
        shutil.copy( dataset.path, output_path )
    else:
        shutil.move( dataset.path, output_path )
    # Write the job info
    info = dict( type = 'dataset',
                 dataset_id = dataset.dataset_id,
                 ext = ext,
                 stdout = 'uploaded %s file' % data_type,
                 name = dataset.name,
                 line_count = line_count )
    json_file.write( to_json_string( info ) + "\n" )

def add_composite_file( dataset, json_file, output_path ):
        if dataset.composite_files:
            os.mkdir( dataset.extra_files_path )
            for name, value in dataset.composite_files.iteritems():
                value = util.bunch.Bunch( **value )
                if dataset.composite_file_paths[ value.name ] is None and not value.optional:
                    file_err( 'A required composite data file was not provided (%s)' % name, dataset, json_file )
                    break
                elif dataset.composite_file_paths[value.name] is not None:
                    if not value.is_binary:
                        if uploaded_dataset.composite_files[ value.name ].space_to_tab:
                            sniff.convert_newlines_sep2tabs( dataset.composite_file_paths[ value.name ][ 'path' ] )
                        else:
                            sniff.convert_newlines( dataset.composite_file_paths[ value.name ][ 'path' ] )
                    shutil.move( dataset.composite_file_paths[ value.name ][ 'path' ], os.path.join( dataset.extra_files_path, name ) )
        # Move the dataset to its "real" path
        shutil.move( dataset.primary_file, output_path )
        # Write the job info
        info = dict( type = 'dataset',
                     dataset_id = dataset.dataset_id,
                     stdout = 'uploaded %s file' % dataset.file_type )
        json_file.write( to_json_string( info ) + "\n" )

def __main__():

    if len( sys.argv ) < 2:
        print >>sys.stderr, 'usage: upload.py <json paramfile> <output spec> ...'
        sys.exit( 1 )

    output_paths = parse_outputs( sys.argv[2:] )

    json_file = open( 'galaxy.json', 'w' )

    for line in open( sys.argv[1], 'r' ):
        dataset = from_json_string( line )
        dataset = util.bunch.Bunch( **safe_dict( dataset ) )

        try:
            output_path = output_paths[int( dataset.dataset_id )]
        except:
            print >>sys.stderr, 'Output path for dataset %s not found on command line' % dataset.dataset_id
            sys.exit( 1 )

        if dataset.type == 'composite':
            add_composite_file( dataset, json_file, output_path )
        else:
            add_file( dataset, json_file, output_path )

    # clean up paramfile
    try:
        os.remove( sys.argv[1] )
    except:
        pass

if __name__ == '__main__':
    __main__()
