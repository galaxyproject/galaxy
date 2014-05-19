"""
Functionality for dealing with dbkeys.
"""
#dbkeys read from disk using builds.txt
from galaxy.util import dbnames
from galaxy.util.json import from_json_string
from galaxy.util.odict import odict
import os.path


class GenomeBuilds( object ):
    default_value = "?"
    default_name = "unspecified (?)"

    def __init__( self, app, data_table_name="__dbkeys__", load_old_style=True ):
        self._app = app
        self._data_table_name = data_table_name
        self._static_chrom_info_path = app.config.len_file_path
        self._static_dbkeys = odict() #need odict to keep ? at top of list
        if load_old_style:
            for key, value in dbnames:
                self._static_dbkeys[ key ] = value

    def get_genome_build_names( self, trans=None ):
        #FIXME: how to deal with key duplicates?
        #Load old builds.txt static keys
        rval = ( self._static_dbkeys.items() )
        #load dbkeys from dbkey data table
        dbkey_table = self._app.tool_data_tables.get( self._data_table_name, None )
        if dbkey_table is not None:
            for field_dict in dbkey_table.get_named_fields_list():
                rval.append( ( field_dict[ 'value' ], field_dict[ 'name' ] ) )
        #load user custom genome builds
        if trans is not None:
            if trans.history:
                datasets = trans.sa_session.query( self._app.model.HistoryDatasetAssociation ) \
                                          .filter_by( deleted=False, history_id=trans.history.id, extension="len" )
                for dataset in datasets:
                    rval.append( (dataset.dbkey, dataset.name) )
            user = trans.get_user()
            if user and 'dbkeys' in user.preferences:
                user_keys = from_json_string( user.preferences['dbkeys'] )
                for key, chrom_dict in user_keys.iteritems():
                    rval.append( ( key, "%s (%s) [Custom]" % ( chrom_dict['name'], key ) ) )
        return rval

    def get_chrom_info( self, dbkey, tool, trans=None ):
        chrom_info = None
        db_dataset = None
        # Collect chromInfo from custom builds
        if trans:
            db_dataset = trans.db_dataset_for( dbkey )
            if db_dataset:
                #incoming[ "chromInfo" ] = db_dataset.file_name
                chrom_info = db_dataset.file_name
            else:
                # -- Get chrom_info (len file) from either a custom or built-in build. --
                if trans.user and ( 'dbkeys' in trans.user.preferences ) and ( dbkey in from_json_string( trans.user.preferences[ 'dbkeys' ] ) ):
                    # Custom build.
                    custom_build_dict = from_json_string( trans.user.preferences[ 'dbkeys' ] )[ dbkey ]
                    # HACK: the attempt to get chrom_info below will trigger the
                    # fasta-to-len converter if the dataset is not available or,
                    # which will in turn create a recursive loop when
                    # running the fasta-to-len tool. So, use a hack in the second
                    # condition below to avoid getting chrom_info when running the
                    # fasta-to-len converter.
                    if 'fasta' in custom_build_dict and tool.id != 'CONVERTER_fasta_to_len':
                        # Build is defined by fasta; get len file, which is obtained from converting fasta.
                        build_fasta_dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( custom_build_dict[ 'fasta' ] )
                        chrom_info = build_fasta_dataset.get_converted_dataset( trans, 'len' ).file_name
                    elif 'len' in custom_build_dict:
                        # Build is defined by len file, so use it.
                        chrom_info = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( custom_build_dict[ 'len' ] ).file_name
        if not chrom_info:
            dbkey_table = self._app.tool_data_tables.get( self._data_table_name, None )
            if dbkey_table is not None:
                chrom_info = dbkey_table.get_entry( 'value', dbkey, 'len_path', default=None )
        if not chrom_info:
            # Default to built-in build.
            chrom_info = os.path.join( self._static_chrom_info_path, "%s.len" % dbkey )
        chrom_info = os.path.abspath( chrom_info )
        return ( chrom_info, db_dataset )
