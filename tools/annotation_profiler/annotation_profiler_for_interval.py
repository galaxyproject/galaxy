#!/usr/bin/env python
#Dan Blankenberg
#For a set of intervals, this tool returns the same set of intervals 
#with 2 additional fields: the name of a Table/Feature and the number of
#bases covered. The original intervals are repeated for each Table/Feature.

import sys, struct, optparse, os, random
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.intervals.io
try:
    import psyco
    psyco.full()
except:
    pass

assert sys.version_info[:2] >= ( 2, 4 )

class CachedRangesInFile:
    fmt = 'I'
    fmt_size = struct.calcsize( fmt )
    def __init__( self, filename ):
        self.file_size = os.stat( filename ).st_size
        self.file = open( filename, 'rb' )
        self.length = int( self.file_size / self.fmt_size / 2 )
        self._cached_ranges = [ None for i in xrange( self.length ) ]
    def __getitem__( self, i ):
        if self._cached_ranges[i] is not None:
            return self._cached_ranges[i]
        if i < 0: i = self.length + i
        offset = i * self.fmt_size * 2
        self.file.seek( offset )
        try:
            start = struct.unpack( self.fmt, self.file.read( self.fmt_size ) )[0]
            end = struct.unpack( self.fmt, self.file.read( self.fmt_size ) )[0]
        except Exception, e:
            raise IndexError, e
        self._cached_ranges[i] = ( start, end )
        return start, end
    def __len__( self ):
        return self.length

class RegionCoverage:
    def __init__( self, filename_base ):
        try:
            self._coverage = CachedRangesInFile( "%s.covered" % filename_base )
        except Exception, e:
            #print "Error loading coverage file %s: %s" % ( "%s.covered" % filename_base, e )
            self._coverage = []
        try: 
            self._total_coverage = int( open( "%s.total_coverage" % filename_base ).read() )
        except Exception, e:
            #print "Error loading total coverage file %s: %s" % ( "%s.total_coverage" % filename_base, e )
            self._total_coverage = 0
    def get_start_index( self, start ):
        #binary search: returns index of range closest to start
        if start > self._coverage[-1][1]:
            return len( self._coverage ) - 1
        i = 0
        j = len( self._coverage) - 1
        while i < j:
            k = ( i + j ) / 2
            if start <= self._coverage[k][1]:
                j = k
            else:
                i = k + 1
        return i
    def get_coverage( self, start, end ):
        if len( self._coverage ) < 1 or start > self._coverage[-1][1] or end < self._coverage[0][0]:
            return 0
        if self._total_coverage and start <= self._coverage[0][0] and end >= self._coverage[-1][1]:
            return self._total_coverage
        coverage = 0
        for i in xrange( self.get_start_index( start ), len( self._coverage ) ):
            c_start, c_end = self._coverage[i]
            if c_start > end:
                break
            if c_start <= end and c_end >= start:
                coverage += min( end, c_end ) - max( start, c_start )
        return coverage

class CachedCoverageReader:
    def __init__( self, base_file_path, buffer = 10, table_names = None ):
        self._base_file_path = base_file_path
        self._buffer = buffer #number of chromosomes to keep in memory at a time
        self._coverage = {}
        if table_names is None: table_names = os.listdir( self._base_file_path )
        for tablename in table_names: self._coverage[tablename] = {}
    def iter_table_coverage_by_region( self, chrom, start, end ):
        for tablename, chromosomes in self._coverage.iteritems():
            if chrom not in chromosomes:
                if len( chromosomes ) >= self._buffer:
                    #randomly remove one chromosome from this table
                    del chromosomes[ chromosomes.keys().pop( random.randint( 0, self._buffer - 1 ) ) ]
                chromosomes[chrom] = RegionCoverage( os.path.join ( self._base_file_path, tablename, chrom ) )
            yield tablename, chromosomes[chrom].get_coverage( start, end )


def __main__():
    parser = optparse.OptionParser()
    parser.add_option(
        '-k','--keep_empty',
        action="store_true",
        dest='keep_empty',
        default=False,
        help='Keep tables with 0 coverage'
    )
    parser.add_option(
        '-b','--buffer',
        dest='buffer',
        type='int',default=10,
        help='Number of Chromosomes to keep buffered'
    )
    parser.add_option(
        '-c','--chrom_col',
        dest='chrom_col',
        type='int',default=1,
        help='Chromosome column'
    )
    parser.add_option(
        '-s','--start_col',
        dest='start_col',
        type='int',default=2,
        help='Start Column'
    )
    parser.add_option(
        '-e','--end_col',
        dest='end_col',
        type='int',default=3,
        help='End Column'
    )
    parser.add_option(
        '-p','--path',
        dest='path',
        type='str',default='/depot/data2/galaxy/annotation_profiler/hg18',
        help='Path to profiled data for this organism'
    )
    parser.add_option(
        '-t','--table_names',
        dest='table_names',
        type='str',default='None',
        help='Path to profiled data for this organism'
    )
    parser.add_option(
        '-i','--input',
        dest='interval_filename',
        type='str',
        help='Input Interval File'
    )
    parser.add_option(
        '-o','--output',
        dest='out_filename',
        type='str',
        help='Input Interval File'
    )
    
    options, args = parser.parse_args()
    
    table_names = options.table_names.split( "," )
    if "None" in table_names: table_names = None
    coverage_reader = CachedCoverageReader( options.path, buffer = options.buffer, table_names = table_names )
    
    out = open( options.out_filename, 'wb' )
    
    for region in bx.intervals.io.NiceReaderWrapper( open( options.interval_filename, 'rb' ), chrom_col = options.chrom_col - 1, start_col = options.start_col - 1, end_col = options.end_col -1 , fix_strand = True, return_header = False, return_comments = False ):
        for tablename, coverage in coverage_reader.iter_table_coverage_by_region( region.chrom, region.start, region.end ):
            if options.keep_empty or coverage:
                #only output regions that have atleast 1 base covered unless empty are requested
                out.write("%s\t%s\t%s\n" % ( "\t".join( region.fields ), tablename, coverage ) )
    out.close()

if __name__ == "__main__": __main__()
