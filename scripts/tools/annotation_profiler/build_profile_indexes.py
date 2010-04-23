#!/usr/bin/env python
#Dan Blankenberg

VERSION = '1.0.0' # version of this script

from optparse import OptionParser
import os, gzip, struct, time
from ftplib import FTP #do we want a diff method than using FTP to determine Chrom Names, eg use local copy

#import md5 from hashlib; if python2.4 or less, use old md5
try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

#import BitSet from bx-python, try using eggs and package resources, fall back to any local installation
try:
    from galaxy import eggs
    import pkg_resources
    pkg_resources.require( "bx-python" )
except: pass #Maybe there is a local installation available
from bx.bitset import BitSet

#Define constants
STRUCT_FMT = '<I'
STRUCT_SIZE = struct.calcsize( STRUCT_FMT )
DEFAULT_BITSET_SIZE = 300000000
CHUNK_SIZE = 1024

#Headers used to parse .sql files to determine column indexes for chromosome name, start and end
alias_spec = { 
    'chromCol'  : [ 'chrom' , 'CHROMOSOME' , 'CHROM', 'Chromosome Name', 'tName' ],  
    'startCol'  : [ 'start' , 'START', 'chromStart', 'txStart', 'Start Position (bp)', 'tStart', 'genoStart' ],
    'endCol'    : [ 'end'   , 'END'  , 'STOP', 'chromEnd', 'txEnd', 'End Position (bp)', 'tEnd', 'genoEnd' ], 
}

#Headers used to parse trackDb.txt.gz
#TODO: these should be parsed directly from trackDb.sql
trackDb_headers = ["tableName", "shortLabel", "type", "longLabel", "visibility", "priority", "colorR", "colorG", "colorB", "altColorR", "altColorG", "altColorB", "useScore", "private", "restrictCount", "restrictList", "url", "html", "grp", "canPack", "settings"]

def get_columns( filename ):
    input_sql = open( filename ).read()
    input_sql = input_sql.split( 'CREATE TABLE ' )[1].split( ';' )[0]
    input_sql = input_sql.split( ' (', 1 )
    table_name = input_sql[0].strip().strip( '`' )
    input_sql = [ split.strip().split( ' ' )[0].strip().strip( '`' ) for split in input_sql[1].rsplit( ')', 1 )[0].strip().split( '\n' ) ]
    print input_sql
    chrom_col = None
    start_col = None
    end_col = None
    for col_name in alias_spec['chromCol']:
        for i, header_name in enumerate( input_sql ):
            if col_name == header_name:
                chrom_col = i
                break
        if chrom_col is not None:
            break
    
    for col_name in alias_spec['startCol']:
        for i, header_name in enumerate( input_sql ):
            if col_name == header_name:
                start_col = i
                break
        if start_col is not None:
            break

    for col_name in alias_spec['endCol']:
        for i, header_name in enumerate( input_sql ):
            if col_name == header_name:
                end_col = i
                break
        if end_col is not None:
            break

    return table_name, chrom_col, start_col, end_col


def create_grouping_xml( input_dir, output_dir, dbkey ):
    output_filename = os.path.join( output_dir, '%s_tables.xml' % dbkey )
    def load_groups( file_name = 'grp.txt.gz' ):
        groups = {}
        for line in gzip.open( os.path.join( input_dir, file_name ) ):
            fields = line.split( '\t' )
            groups[fields[0]] = { 'desc': fields[1], 'priority':  fields[2] }
        return groups
    f = gzip.open( os.path.join( input_dir, 'trackDb.txt.gz' ) )
    out = open( output_filename, 'wb' )
    tables = {}
    cur_buf = ''
    while True:
        line = f.readline()
        if not line: break
        #remove new lines
        line = line.rstrip( '\n\r' )
        line = line.replace( '\\\t', ' ' ) #replace escaped tabs with space
        cur_buf += "%s\n" % line.rstrip( '\\' )
        if line.endswith( '\\' ):
            continue #line is wrapped, next line
        #all fields should be loaded now...
        fields = cur_buf.split( '\t' )
        cur_buf = '' #reset buffer
        assert len( fields ) == len( trackDb_headers ), 'Failed Parsing trackDb.txt.gz; fields: %s' % fields
        table_name = fields[ 0 ]
        tables[ table_name ] = {}
        for field_name, field_value in zip( trackDb_headers, fields ):
            tables[ table_name ][ field_name ] = field_value
        #split settings fields into dict
        fields = fields[-1].split( '\n' )
        tables[ table_name ][ 'settings' ] = {}
        for field in fields:
            setting_fields = field.split( ' ', 1 )
            setting_name = setting_value = setting_fields[ 0 ]
            if len( setting_fields ) > 1:
                setting_value = setting_fields[ 1 ]
            if setting_name or setting_value:
                tables[ table_name ][ 'settings' ][ setting_name ] = setting_value
    #Load Groups
    groups = load_groups()
    in_groups = {}
    for table_name, values in tables.iteritems():
        if os.path.exists( os.path.join( output_dir, table_name ) ):
            group = values['grp']
            if group not in in_groups:
                in_groups[group]={}
            #***NAME CHANGE***, 'subTrack' no longer exists as a setting...use 'parent' instead
            #subTrack = values.get('settings', {} ).get( 'subTrack', table_name )
            subTrack = values.get('settings', {} ).get( 'parent', table_name ).split( ' ' )[0] #need to split, because could be e.g. 'trackgroup on'
            if subTrack not in in_groups[group]:
                in_groups[group][subTrack]=[]
            in_groups[group][subTrack].append( table_name )
    
    assigned_tables = []
    out.write( """<filter type="data_meta" data_ref="input1" meta_key="dbkey" value="%s">\n""" % ( dbkey ) )
    out.write( "  <options>\n" )
    for group, subTracks in sorted( in_groups.iteritems() ):
        out.write( """    <option name="%s" value="group-%s">\n""" % ( groups[group]['desc'], group ) )
        for sub_name, sub_tracks in subTracks.iteritems():
            if len( sub_tracks ) > 1:
                out.write( """      <option name="%s" value="subtracks-%s">\n""" % ( sub_name, sub_name ) )
                sub_tracks.sort()
                for track in sub_tracks:
                    track_label = track
                    if "$" not in tables[track]['shortLabel']:
                        track_label = tables[track]['shortLabel']
                    out.write( """        <option name="%s" value="%s"/>\n""" % ( track_label, track ) )
                    assigned_tables.append( track )
                out.write( "      </option>\n" )
            else:
                track = sub_tracks[0]
                track_label = track
                if "$" not in tables[track]['shortLabel']:
                    track_label = tables[track]['shortLabel']
                out.write( """        <option name="%s" value="%s"/>\n""" % ( track_label, track ) )
                assigned_tables.append( track )
        out.write( "    </option>\n" )
    unassigned_tables = list( sorted( [ table_dir for table_dir in os.listdir( output_dir ) if table_dir not in assigned_tables and os.path.isdir( os.path.join( output_dir, table_dir ) ) ] ) )
    if unassigned_tables:
        out.write( """    <option name="Uncategorized Tables" value="group-trackDbUnassigned">\n""" )
        for table_name in unassigned_tables:
            out.write( """        <option name="%s" value="%s"/>\n""" % ( table_name, table_name ) )
        out.write( "    </option>\n" )
    out.write( "  </options>\n" )
    out.write( """</filter>\n""" )
    out.close()

def write_database_dump_info( input_dir, output_dir, dbkey, chrom_lengths, default_bitset_size ):
    #generate hash for profiled table directories
    #sort directories off output root (files in output root not hashed, including the profiler_info.txt file)
    #sort files in each directory and hash file contents
    profiled_hash = md5()
    for table_dir in sorted( [ table_dir for table_dir in os.listdir( output_dir ) if os.path.isdir( os.path.join( output_dir, table_dir ) ) ] ):
        for filename in sorted( os.listdir( os.path.join( output_dir, table_dir ) ) ):
            f  = open( os.path.join( output_dir, table_dir, filename ), 'rb' )
            while True:
                hash_chunk = f.read( CHUNK_SIZE )
                if not hash_chunk:
                    break
                profiled_hash.update( hash_chunk )
    profiled_hash = profiled_hash.hexdigest()
    
    #generate hash for input dir
    #sort directories off input root
    #sort files in each directory and hash file contents
    database_hash = md5()
    for dirpath, dirnames, filenames in sorted( os.walk( input_dir ) ):
        for filename in sorted( filenames ):
            f  = open( os.path.join( input_dir, dirpath, filename ), 'rb' )
            while True:
                hash_chunk = f.read( CHUNK_SIZE )
                if not hash_chunk:
                    break
                database_hash.update( hash_chunk )
    database_hash = database_hash.hexdigest()
    
    #write out info file
    out = open( os.path.join( output_dir, 'profiler_info.txt' ), 'wb' )
    out.write( 'dbkey\t%s\n' % ( dbkey ) )
    out.write( 'chromosomes\t%s\n' % ( ','.join( [ '%s=%s' % ( chrom_name, chrom_len ) for chrom_name, chrom_len in chrom_lengths.iteritems() ] ) ) )
    out.write( 'bitset_size\t%s\n' % ( default_bitset_size ) )
    for line in open( os.path.join( input_dir, 'trackDb.sql' ) ):
        line = line.strip()
        if line.startswith( '-- Dump completed on ' ):
            line = line[ len( '-- Dump completed on ' ): ]
            out.write( 'dump_time\t%s\n' % ( line ) )
            break
    out.write( 'dump_hash\t%s\n' % ( database_hash ) )
    out.write( 'profiler_time\t%s\n' % ( time.time() ) )
    out.write( 'profiler_hash\t%s\n' % ( profiled_hash ) )
    out.write( 'profiler_version\t%s\n' % ( VERSION ) )
    out.write( 'profiler_struct_format\t%s\n' % ( STRUCT_FMT ) )
    out.write( 'profiler_struct_size\t%s\n' % ( STRUCT_SIZE ) )
    out.close()
    
def __main__():
    usage = "usage: %prog options"
    parser = OptionParser( usage=usage )
    parser.add_option( '-d', '--dbkey', dest='dbkey', default='hg18', help='dbkey to process' )
    parser.add_option( '-i', '--input_dir', dest='input_dir', default=os.path.join( 'golden_path','%s', 'database' ), help='Input Directory' )
    parser.add_option( '-o', '--output_dir', dest='output_dir', default=os.path.join( 'profiled_annotations','%s' ), help='Output Directory' )
    parser.add_option( '-c', '--chromosomes', dest='chromosomes', default='', help='Comma separated list of: ChromName1[=length],ChromName2[=length],...' )
    parser.add_option( '-b', '--bitset_size', dest='bitset_size', default=DEFAULT_BITSET_SIZE, type='int', help='Default BitSet size; overridden by sizes specified in chromInfo.txt.gz or by --chromosomes' )
    parser.add_option( '-f', '--ftp_site', dest='ftp_site', default='hgdownload.cse.ucsc.edu', help='FTP site; used for chromosome info when chromInfo.txt.gz method fails' )
    parser.add_option( '-p', '--ftp_path', dest='ftp_path', default='/goldenPath/%s/chromosomes/', help='FTP Path; used for chromosome info when chromInfo.txt.gz method fails' )
    
    ( options, args ) = parser.parse_args()
    
    input_dir = options.input_dir
    if '%' in input_dir:
        input_dir = input_dir % options.dbkey
    assert os.path.exists( input_dir ), 'Input directory does not exist'
    output_dir = options.output_dir
    if '%' in output_dir:
        output_dir = output_dir % options.dbkey
    assert not os.path.exists( output_dir ), 'Output directory already exists'
    os.makedirs( output_dir )
    ftp_path = options.ftp_path
    if '%' in ftp_path:
        ftp_path = ftp_path % options.dbkey
    
    #Get chromosome names and lengths
    chrom_lengths = {}
    if options.chromosomes:
        for chrom in options.chromosomes.split( ',' ):
            fields = chrom.split( '=' )
            chrom = fields[0]
            if len( fields ) > 1:
                chrom_len = int( fields[1] )
            else:
                chrom_len = options.bitset_size
            chrom_lengths[ chrom ] = chrom_len
        chroms = chrom_lengths.keys()
        print 'Chrom info taken from command line option.'
    else:
        try:
            for line in gzip.open( os.path.join( input_dir, 'chromInfo.txt.gz' ) ):
                fields = line.strip().split( '\t' )
                chrom_lengths[ fields[0] ] = int( fields[ 1 ] )
            chroms = chrom_lengths.keys()
            print 'Chrom info taken from chromInfo.txt.gz.'
        except Exception, e:
            print 'Error loading chrom info from chromInfo.txt.gz, trying FTP method.'
            chrom_lengths = {} #zero out chrom_lengths
            chroms = []
            ftp = FTP( options.ftp_site )
            ftp.login()
            for name in ftp.nlst( ftp_path ):
                if name.endswith( '.fa.gz' ):
                    chroms.append( name.split( '/' )[-1][ :-len( '.fa.gz' ) ] )
            ftp.close()
            for chrom in chroms:
                chrom_lengths[ chrom ] = options.bitset_size
    #sort chroms by length of name, decending; necessary for when table names start with chrom name
    chroms = list( reversed( [ chrom for chrom_len, chrom in sorted( [ ( len( chrom ), chrom ) for chrom in chroms ] ) ] ) )
    
    #parse tables from local files
    #loop through directory contents, if file ends in '.sql', process table
    for filename in os.listdir( input_dir ):
        if filename.endswith ( '.sql' ):
            base_filename = filename[ 0:-len( '.sql' ) ]
            table_out_dir = os.path.join( output_dir, base_filename )
            #some tables are chromosome specific, lets strip off the chrom name
            for chrom in chroms:
                if base_filename.startswith( "%s_" % chrom ):
                    #found chromosome
                    table_out_dir = os.path.join( output_dir, base_filename[len( "%s_" % chrom ):] )
                    break
            #create table dir
            if not os.path.exists( table_out_dir ):
                os.mkdir( table_out_dir ) #table dir may already exist in the case of single chrom tables
                print "Created table dir (%s)." % table_out_dir
            else:
                print "Table dir (%s) already exists." % table_out_dir
            #find column assignments
            table_name, chrom_col, start_col, end_col = get_columns( "%s.sql" % os.path.join( input_dir, base_filename ) )
            if chrom_col is None or start_col is None or end_col is None:
                print "Table %s (%s) does not appear to have a chromosome, a start, or a stop." % ( table_name, "%s.sql" % os.path.join( input_dir, base_filename ) )
                if not os.listdir( table_out_dir ):
                    print "Removing empty table (%s) directory (%s)." % ( table_name, table_out_dir )
                    os.rmdir( table_out_dir )
                continue
            #build bitsets from table
            bitset_dict = {}
            for line in gzip.open( '%s.txt.gz' % os.path.join( input_dir, base_filename )  ):
                fields = line.strip().split( '\t' )
                chrom = fields[ chrom_col ]
                start = int( fields[ start_col ] )
                end = int( fields[ end_col ] )
                if chrom not in bitset_dict:
                    bitset_dict[ chrom ] = BitSet( chrom_lengths.get( chrom, options.bitset_size ) )
                bitset_dict[ chrom ].set_range(  start, end - start  )
            #write bitsets as profiled annotations
            for chrom_name, chrom_bits in bitset_dict.iteritems():
                out = open( os.path.join( table_out_dir, '%s.covered' % chrom_name  ), 'wb' )
                end = 0
                total_regions = 0
                total_coverage = 0
                max_size = chrom_lengths.get( chrom_name, options.bitset_size )
                while True:
                    start = chrom_bits.next_set( end )
                    if start >= max_size:
                        break
                    end = chrom_bits.next_clear( start )
                    out.write( struct.pack( STRUCT_FMT, start ) )
                    out.write( struct.pack( STRUCT_FMT, end ) )
                    total_regions += 1
                    total_coverage += end - start
                    if end >= max_size:
                        break
                out.close()
                open( os.path.join( table_out_dir, '%s.total_regions' % chrom_name  ), 'wb' ).write( str( total_regions ) )
                open( os.path.join( table_out_dir, '%s.total_coverage' % chrom_name  ), 'wb' ).write( str( total_coverage ) )
    
    #create xml
    create_grouping_xml( input_dir, output_dir, options.dbkey )
    #create database dump info file, for database version control
    write_database_dump_info( input_dir, output_dir, options.dbkey, chrom_lengths, options.bitset_size )
    
if __name__ == "__main__": __main__()
