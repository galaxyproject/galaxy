#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

NOTE: This should not be called directly. Use the set_metadata.sh script in Galaxy's
top level directly.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
    -D, --delete_dir: delete attribute files' directory if operation completed successfully
"""
from galaxy import eggs
import os, pkg_resources, tempfile, tarfile
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from galaxy.util.json import *
from warnings import warn
from bx.cookbook import doc_optparse

def create_archive( history_attrs_file, datasets_attrs_file, jobs_attrs_file, out_file, gzip=False ):
    """ Create archive from the given attribute/metadata files and save it to out_file. """
    tarfile_mode = "w"
    if gzip:
        tarfile_mode += ":gz"
    try:
    
        history_archive = tarfile.open( out_file, tarfile_mode )
    
        # Read datasets attributes from file.
        datasets_attr_in = open( datasets_attrs_file, 'rb' )
        datasets_attr_str = ''
        buffsize = 1048576
        try:
            while True:
                datasets_attr_str += datasets_attr_in.read( buffsize )
                if not datasets_attr_str or len( datasets_attr_str ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        datasets_attr_in.close()
        datasets_attrs = from_json_string( datasets_attr_str )
    
        # Add datasets to archive and update dataset attributes.
        # TODO: security check to ensure that files added are in Galaxy dataset directory?
        for dataset_attrs in datasets_attrs:
            dataset_file_name = dataset_attrs[ 'file_name' ] # Full file name.
            dataset_archive_name = os.path.join( "datasets", os.path.split( dataset_file_name )[-1] )
            history_archive.add( dataset_file_name, arcname=dataset_archive_name )
            # Update dataset filename to be archive name.
            dataset_attrs[ 'file_name' ] = dataset_archive_name
    
        # Rewrite dataset attributes file.
        datasets_attrs_out = open( datasets_attrs_file, 'w' )
        datasets_attrs_out.write( to_json_string( datasets_attrs ) )
        datasets_attrs_out.close()
    
        # Finish archive.
        history_archive.add( history_attrs_file, arcname="history_attrs.txt" )
        history_archive.add( datasets_attrs_file, arcname="datasets_attrs.txt" )
        history_archive.add( jobs_attrs_file, arcname="jobs_attrs.txt" )
        history_archive.close()
        
        # Status.
        return 'Created history archive.'
    except Exception, e:
        return 'Error creating history archive: %s' + str( e ), sys.stderr

if __name__ == "__main__":
    # Parse command line.
    options, args = doc_optparse.parse( __doc__ )
    try:
        gzip = bool( options.gzip )
        delete_dir = bool( options.delete_dir )
        history_attrs, dataset_attrs, job_attrs, out_file = args
    except:
        doc_optparse.exception()
    
    # Create archive.
    status = create_archive( history_attrs, dataset_attrs, job_attrs, out_file, gzip )
    print status