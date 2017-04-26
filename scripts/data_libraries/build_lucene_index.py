#!/usr/bin/env python
"""
Build index for full-text lucene search of files in data libraries.

Requires a full text search server and configuration settings in
galaxy.ini. See the lucene settings in the data library search section for more
details.

Run from the ~/scripts/data_libraries directory:
%sh build_lucene_index.sh
"""
import ConfigParser
import csv
import os
import sys
import urllib
import urllib2

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.model.mapping
from galaxy import config, model


def main( ini_file ):
    sa_session, gconfig = get_sa_session( ini_file )
    max_size = float( gconfig.get( "fulltext_max_size", 100 ) ) * 1048576
    ignore_exts = gconfig.get( "fulltext_noindex_filetypes", "" ).split( "," )
    search_url = gconfig.get( "fulltext_url", None )
    if not search_url:
        raise ValueError( "Need to specify search functionality in galaxy.ini" )
    dataset_file = create_dataset_file( get_lddas( sa_session, max_size, ignore_exts ) )
    try:
        build_index( search_url, dataset_file )
    finally:
        if os.path.exists( dataset_file ):
            os.remove( dataset_file )


def build_index( search_url, dataset_file ):
    url = "%s/index?%s" % ( search_url, urllib.urlencode( { "docfile": dataset_file } ) )
    request = urllib2.Request( url )
    request.get_method = lambda: "PUT"
    urllib2.urlopen( request )


def create_dataset_file( dataset_iter ):
    dataset_file = os.path.join( os.getcwd(), "full-text-search-files.csv" )
    out_handle = open( dataset_file, "w" )
    writer = csv.writer( out_handle )
    for did, dfile, dname in dataset_iter:
        writer.writerow( [ did, dfile, dname ] )
    out_handle.close()
    return dataset_file


def get_lddas( sa_session, max_size, ignore_exts ):
    for ldda in sa_session.query( model.LibraryDatasetDatasetAssociation ).filter_by( deleted=False ):
        if ( float( ldda.dataset.get_size() ) > max_size or ldda.extension in ignore_exts ):
            fname = ""
        else:
            fname = ldda.dataset.get_file_name()
        yield ldda.id, fname, _get_dataset_metadata(ldda).replace("\n", " ")


def _get_dataset_metadata(ldda):
    """Retrieve descriptions and information associated with a dataset.
    """
    lds = ldda.library_dataset
    folder_info = _get_folder_info(lds.folder)
    lds_info = lds.get_info()
    if lds_info and not lds_info.startswith("upload"):
        lds_info = lds_info.replace("no info", "")
    else:
        lds_info = ""
    return "%s %s %s %s %s" % (lds.name or "", lds_info, ldda.metadata.dbkey,
                               ldda.message, folder_info)


def _get_folder_info(folder):
    """Get names and descriptions for all parent folders except top level.
    """
    folder_info = ""
    if folder and folder.parent:
        folder_info = _get_folder_info(folder.parent)
        folder_info += " %s %s" % (
            folder.name.replace("Unnamed folder", ""),
            folder.description or "")
    return folder_info


def get_sa_session( ini_file ):
    conf_parser = ConfigParser.ConfigParser( { 'here': os.getcwd() } )
    conf_parser.read( ini_file )
    kwds = dict()
    for key, value in conf_parser.items( "app:main" ):
        kwds[ key ] = value
    ini_config = config.Configuration( **kwds )
    db_con = ini_config.database_connection
    if not db_con:
        db_con = "sqlite:///%s?isolation_level=IMMEDIATE" % ini_config.database
    model = galaxy.model.mapping.init( ini_config.file_path,
                                       db_con,
                                       engine_options={},
                                       create_tables=False )
    return model.context.current, ini_config


if __name__ == "__main__":
    main( *sys.argv[1:] )
