import os, re, sys, glob, logging
from bx.seq.twobit import TwoBitFile
from galaxy.util.json import loads
from galaxy import model, util
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

# FIXME: copied from tracks.py
# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    NO_CONVERTER = "no converter",
    NO_TOOL = "no tool",
    DATA = "data",
    ERROR = "error",
    OK = "ok"
)

def decode_dbkey( dbkey ):
    """ Decodes dbkey and returns tuple ( username, dbkey )"""
    if ':' in dbkey:
        return dbkey.split( ':' )
    else:
        return None, dbkey

class GenomeRegion( object ):
    """
    A genomic region on an individual chromosome.
    """

    def __init__( self, chrom = None, start = 0, end = 0, sequence=None ):
        self.chrom = chrom
        self.start = int( start )
        self.end = int( end )
        self.sequence = sequence

    def __str__( self ):
        return self.chrom + ":" + str( self.start ) + "-" + str( self.end )

    @staticmethod
    def from_dict( obj_dict ):
        return GenomeRegion( chrom = obj_dict[ 'chrom' ],
                             start = obj_dict[ 'start' ],
                             end   = obj_dict[ 'end' ] )

    @staticmethod
    def from_str( obj_str ):
        # check for gene region
        gene_region = obj_str.split(':')

        # split gene region into components
        if (len(gene_region) == 2):
            gene_interval = gene_region[1].split('-')

            # check length
            if (len(gene_interval) == 2):
                return GenomeRegion(chrom = gene_region[0],
                                    start = gene_interval[0],
                                    end   = gene_interval[1])

        # return genome region instance
        return GenomeRegion()

class Genome( object ):
    """
    Encapsulates information about a known genome/dbkey.
    """
    def __init__( self, key, description, len_file=None, twobit_file=None ):
        self.key = key
        self.description = description
        self.len_file = len_file
        self.twobit_file = twobit_file

    def to_dict( self, num=None, chrom=None, low=None ):
        """
        Returns representation of self as a dictionary.
        """

        def check_int(s):
            if s.isdigit():
                return int(s)
            else:
                return s

        def split_by_number(s):
            return [ check_int(c) for c in re.split('([0-9]+)', s) ]

        #
        # Parameter check, setting.
        #
        if num:
            num = int( num )
        else:
            num = sys.maxint

        if low:
            low = int( low )
            if low < 0:
                low = 0
        else:
            low = 0

        #
        # Get chroms data:
        #   (a) chrom name, len;
        #   (b) whether there are previous, next chroms;
        #   (c) index of start chrom.
        #
        len_file_enumerate = enumerate( open( self.len_file ) )
        chroms = {}
        prev_chroms = False
        start_index = 0
        if chrom:
            # Use starting chrom to start list.
            found = False
            count = 0
            for line_num, line in len_file_enumerate:
                if line.startswith("#"):
                    continue
                name, len = line.split("\t")
                if found:
                    chroms[ name ] = int( len )
                    count += 1
                elif name == chrom:
                    # Found starting chrom.
                    chroms[ name ] = int ( len )
                    count += 1
                    found = True
                    start_index = line_num
                    if line_num != 0:
                        prev_chroms = True
                if count >= num:
                    break
        else:
            # Use low to start list.
            high = low + int( num )
            prev_chroms = ( low != 0 )
            start_index = low

            # Read chrom data from len file.
            for line_num, line in len_file_enumerate:
                if line_num < low:
                    continue
                if line_num >= high:
                    break
                if line.startswith("#"):
                    continue
                # LEN files have format:
                #   <chrom_name><tab><chrom_length>
                fields = line.split("\t")
                chroms[ fields[0] ] = int( fields[1] )

        # Set flag to indicate whether there are more chroms after list.
        next_chroms = False
        try:
            len_file_enumerate.next()
            next_chroms = True
        except:
            # No more chroms to read.
            pass

        to_sort = [{ 'chrom': chrm, 'len': length } for chrm, length in chroms.iteritems()]
        to_sort.sort(lambda a,b: cmp( split_by_number(a['chrom']), split_by_number(b['chrom']) ))
        return {
            'id': self.key,
            'reference': self.twobit_file is not None,
            'chrom_info': to_sort,
            'prev_chroms' : prev_chroms,
            'next_chroms' : next_chroms,
            'start_index' : start_index
            }

class Genomes( object ):
    """
    Provides information about available genome data and methods for manipulating that data.
    """

    def __init__( self, app ):
        # Create list of genomes from app.genome_builds
        self.genomes = {}
        for key, description in app.genome_builds.get_genome_build_names():
            self.genomes[ key ] = Genome( key, description )

        # Add len files to genomes.
        len_files = glob.glob( os.path.join( app.config.len_file_path, "*.len" ) )
        for f in len_files:
            key = os.path.split( f )[1].split( ".len" )[0]
            if key in self.genomes:
                self.genomes[ key ].len_file = f

        # Add genome data (twobit files) to genomes.
        try:
            for line in open( os.path.join( app.config.tool_data_path, "twobit.loc" ) ):
                if line.startswith("#"): continue
                val = line.split()
                if len( val ) == 2:
                    key, path = val
                    if key in self.genomes:
                        self.genomes[ key ].twobit_file = path
        except IOError, e:
            # Thrown if twobit.loc does not exist.
            log.exception( str( e ) )

    def get_build( self, dbkey ):
        """ Returns build for the given key. """
        rval = None
        if dbkey in self.genomes:
            rval = self.genomes[ dbkey ]
        return rval

    def get_dbkeys( self, trans, chrom_info=False, **kwd ):
        """ Returns all known dbkeys. If chrom_info is True, only dbkeys with
            chromosome lengths are returned. """
        dbkeys = []

        # Add user's custom keys to dbkeys.
        user_keys_dict = {}
        user = trans.get_user()
        if user:
            if 'dbkeys' in user.preferences:
                user_keys_dict = loads( user.preferences[ 'dbkeys' ] )
            dbkeys.extend( [ (attributes[ 'name' ], key ) for key, attributes in user_keys_dict.items() ] )

        # Add app keys to dbkeys.

        # If chrom_info is True, only include keys with len files (which contain chromosome info).
        filter_fn = lambda b: True
        if chrom_info:
            filter_fn = lambda b: b.len_file is not None

        dbkeys.extend( [ ( genome.description, genome.key ) for key, genome in self.genomes.items() if filter_fn( genome ) ] )

        return dbkeys


    def chroms( self, trans, dbkey=None, num=None, chrom=None, low=None ):
        """
        Returns a naturally sorted list of chroms/contigs for a given dbkey.
        Use either chrom or low to specify the starting chrom in the return list.
        """

        # If there is no dbkey owner, default to current user.
        dbkey_owner, dbkey = decode_dbkey( dbkey )
        if dbkey_owner:
            dbkey_user = trans.sa_session.query( trans.app.model.User ).filter_by( username=dbkey_owner ).first()
        else:
            dbkey_user = trans.user

        #
        # Get/create genome object.
        #
        genome = None
        twobit_file = None

        # Look first in user's custom builds.
        if dbkey_user and 'dbkeys' in dbkey_user.preferences:
            user_keys = loads( dbkey_user.preferences['dbkeys'] )
            if dbkey in user_keys:
                dbkey_attributes = user_keys[ dbkey ]
                dbkey_name = dbkey_attributes[ 'name' ]

                # If there's a fasta for genome, convert to 2bit for later use.
                if 'fasta' in dbkey_attributes:
                    build_fasta = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dbkey_attributes[ 'fasta' ] )
                    len_file = build_fasta.get_converted_dataset( trans, 'len' ).file_name
                    build_fasta.get_converted_dataset( trans, 'twobit' )
                    # HACK: set twobit_file to True rather than a file name because
                    # get_converted_dataset returns null during conversion even though
                    # there will eventually be a twobit file available for genome.
                    twobit_file = True
                # Backwards compatibility: look for len file directly.
                elif 'len' in dbkey_attributes:
                    len_file = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( user_keys[ dbkey ][ 'len' ] ).file_name
                if len_file:
                    genome = Genome( dbkey, dbkey_name, len_file=len_file, twobit_file=twobit_file )


        # Look in history and system builds.
        if not genome:
            # Look in history for chromosome len file.
            len_ds = trans.db_dataset_for( dbkey )
            if len_ds:
                genome = Genome( dbkey, dbkey_name, len_file=len_ds.file_name )
            # Look in system builds.
            elif dbkey in self.genomes:
                genome = self.genomes[ dbkey ]

        # Set up return value or log exception if genome not found for key.
        rval = None
        if genome:
            rval = genome.to_dict( num=num, chrom=chrom, low=low )
        else:
            log.exception( 'genome not found for key %s' % dbkey )

        return rval


    def has_reference_data( self, dbkey, dbkey_owner=None ):
        """
        Returns true if there is reference data for the specified dbkey. If dbkey is custom,
        dbkey_owner is needed to determine if there is reference data.
        """
        # Look for key in built-in builds.
        if dbkey in self.genomes and self.genomes[ dbkey ].twobit_file:
            # There is built-in reference data.
            return True

        # Look for key in owner's custom builds.
        if dbkey_owner and 'dbkeys' in dbkey_owner.preferences:
            user_keys = loads( dbkey_owner.preferences[ 'dbkeys' ] )
            if dbkey in user_keys:
                dbkey_attributes = user_keys[ dbkey ]
                if 'fasta' in dbkey_attributes:
                    # Fasta + converted datasets can provide reference data.
                    return True

        return False

    def reference( self, trans, dbkey, chrom, low, high ):
        """
        Return reference data for a build.
        """

        # If there is no dbkey owner, default to current user.
        dbkey_owner, dbkey = decode_dbkey( dbkey )
        if dbkey_owner:
            dbkey_user = trans.sa_session.query( trans.app.model.User ).filter_by( username=dbkey_owner ).first()
        else:
            dbkey_user = trans.user

        if not self.has_reference_data( dbkey, dbkey_user ):
            return None

        #
        # Get twobit file with reference data.
        #
        twobit_file_name = None
        if dbkey in self.genomes:
            # Built-in twobit.
            twobit_file_name = self.genomes[dbkey].twobit_file
        else:
            user_keys = loads( dbkey_user.preferences['dbkeys'] )
            dbkey_attributes = user_keys[ dbkey ]
            fasta_dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dbkey_attributes[ 'fasta' ] )
            msg = fasta_dataset.convert_dataset( trans, 'twobit' )
            if msg:
                return msg
            else:
                twobit_dataset = fasta_dataset.get_converted_dataset( trans, 'twobit' )
                twobit_file_name = twobit_dataset.file_name

        # Read and return reference data.
        try:
            twobit = TwoBitFile( open( twobit_file_name ) )
            if chrom in twobit:
                seq_data = twobit[chrom].get( int(low), int(high) )
                return GenomeRegion( chrom=chrom, start=low, end=high, sequence=seq_data )
        except IOError:
            return None
