"""
Functionality for dealing with dbkeys.
"""
#dbkeys read from disk using builds.txt
from galaxy.util import read_dbnames
from galaxy.util.json import loads
import os.path


class GenomeBuilds( object ):
    default_value = "?"
    default_name = "unspecified (?)"

    def __init__( self, app, data_table_name="__dbkeys__", load_old_style=True ):
        self._app = app
        self._data_table_name = data_table_name
        self._static_chrom_info_path = app.config.len_file_path
        # A dbkey can be listed multiple times, but with different names, so we can't use dictionaries for lookups
        if load_old_style:
            self._static_dbkeys = list( read_dbnames( app.config.builds_file_path ) )
        else:
            self._static_dbkeys = []

    def get_genome_build_names( self, trans=None ):
        # FIXME: how to deal with key duplicates?
        rval = []
        # load user custom genome builds
        if trans is not None:
            if trans.history:
                # This is a little bit Odd. We are adding every .len file in the current history to dbkey list,
                # but this is previous behavior from trans.db_names, so we'll continue to do it.
                # It does allow one-off, history specific dbkeys to be created by a user. But we are not filtering,
                # so a len file will be listed twice (as the build name and again as dataset name), 
                # if custom dbkey creation/conversion occurred within the current history.
                datasets = trans.sa_session.query( self._app.model.HistoryDatasetAssociation ) \
                                          .filter_by( deleted=False, history_id=trans.history.id, extension="len" )
                for dataset in datasets:
                    rval.append( ( dataset.dbkey, "%s (%s) [History]" % ( dataset.name, dataset.dbkey ) ) )
            user = trans.user
            if user and 'dbkeys' in user.preferences:
                user_keys = loads( user.preferences['dbkeys'] )
                for key, chrom_dict in user_keys.iteritems():
                    rval.append( ( key, "%s (%s) [Custom]" % ( chrom_dict['name'], key ) ) )
        # Load old builds.txt static keys
        rval.extend( self._static_dbkeys )
        #load dbkeys from dbkey data table
        dbkey_table = self._app.tool_data_tables.get( self._data_table_name, None )
        if dbkey_table is not None:
            for field_dict in dbkey_table.get_named_fields_list():
                rval.append( ( field_dict[ 'value' ], field_dict[ 'name' ] ) )
        return rval

    def get_chrom_info( self, dbkey, trans=None, custom_build_hack_get_len_from_fasta_conversion=True ):
        # FIXME: flag to turn off custom_build_hack_get_len_from_fasta_conversion should not be required 
        chrom_info = None
        db_dataset = None
        # Collect chromInfo from custom builds
        if trans:
            db_dataset = trans.db_dataset_for( dbkey )
            if db_dataset:
                chrom_info = db_dataset.file_name
            else:
                # Do Custom Build handling
                if trans.user and ( 'dbkeys' in trans.user.preferences ) and ( dbkey in loads( trans.user.preferences[ 'dbkeys' ] ) ):
                    custom_build_dict = loads( trans.user.preferences[ 'dbkeys' ] )[ dbkey ]
                    # HACK: the attempt to get chrom_info below will trigger the
                    # fasta-to-len converter if the dataset is not available or,
                    # which will in turn create a recursive loop when
                    # running the fasta-to-len tool. So, use a hack in the second
                    # condition below to avoid getting chrom_info when running the
                    # fasta-to-len converter.
                    if 'fasta' in custom_build_dict and custom_build_hack_get_len_from_fasta_conversion:
                        # Build is defined by fasta; get len file, which is obtained from converting fasta.
                        build_fasta_dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( custom_build_dict[ 'fasta' ] )
                        chrom_info = build_fasta_dataset.get_converted_dataset( trans, 'len' ).file_name
                    elif 'len' in custom_build_dict:
                        # Build is defined by len file, so use it.
                        chrom_info = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( custom_build_dict[ 'len' ] ).file_name
        # Check Data table
        if not chrom_info:
            dbkey_table = self._app.tool_data_tables.get( self._data_table_name, None )
            if dbkey_table is not None:
                chrom_info = dbkey_table.get_entry( 'value', dbkey, 'len_path', default=None )
        # use configured server len path
        if not chrom_info:
            # Default to built-in build.
            chrom_info = os.path.join( self._static_chrom_info_path, "%s.len" % dbkey )
        chrom_info = os.path.abspath( chrom_info )
        return ( chrom_info, db_dataset )
