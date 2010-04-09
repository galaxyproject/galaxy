#Dan Blankenberg
from optparse import OptionParser
from galaxy_utils.sequence.fastq import fastqReader, fastqWriter

def mean( score_list ):
    return float( sum( score_list ) ) / float( len( score_list ) )

ACTION_METHODS = { 'min':min, 'max':max, 'sum':sum, 'mean':mean }

def compare( aggregated_value, operator, threshold_value ):
    if operator == '>':
        return aggregated_value > threshold_value
    elif operator == '>=':
        return aggregated_value >= threshold_value
    elif operator == '==':
        return aggregated_value == threshold_value
    elif operator == '<':
        return aggregated_value < threshold_value
    elif operator == '<=':
        return aggregated_value <= threshold_value
    elif operator == '!=':
        return aggregated_value != threshold_value

def exclude( value_list, exclude_indexes ):
    rval = []
    for i, val in enumerate( value_list ):
        if i not in exclude_indexes:
            rval.append( val )
    return rval

def exclude_and_compare( aggregate_action, aggregate_list, operator, threshold_value, exclude_indexes = None ):
    if not aggregate_list or compare( aggregate_action( aggregate_list ), operator, threshold_value ):
        return True
    if exclude_indexes:
        for exclude_index in exclude_indexes:
            excluded_list = exclude( aggregate_list, exclude_index )
            if not excluded_list or compare( aggregate_action( excluded_list ), operator, threshold_value ):
                return True
    return False

def main():
    usage = "usage: %prog [options] input_file output_file"
    parser = OptionParser( usage=usage )
    parser.add_option( '-f', '--format', dest='format', type='choice', default='sanger', choices=( 'sanger', 'cssanger', 'solexa', 'illumina' ), help='FASTQ variant type' )
    parser.add_option( '-s', '--window_size', type="int", dest='window_size', default='1', help='Window size' )
    parser.add_option( '-t', '--window_step', type="int", dest='window_step', default='1', help='Window step' )
    parser.add_option( '-e', '--trim_ends', type="choice", dest='trim_ends', default='53', choices=('5','3','53','35' ), help='Ends to Trim' )
    parser.add_option( '-a', '--aggregation_action', type="choice", dest='aggregation_action', default='min', choices=('min','max','sum','mean' ), help='Aggregate action for window' )
    parser.add_option( '-x', '--exclude_count', type="int", dest='exclude_count', default='0', help='Maximum number of bases to exclude from the window during aggregation' )
    parser.add_option( '-c', '--score_comparison', type="choice", dest='score_comparison', default='>=', choices=('>','>=','==','<', '<=', '!=' ), help='Keep read when aggregate score is' )
    parser.add_option( '-q', '--quality_score', type="float", dest='quality_score', default='0', help='Quality Score' )
    parser.add_option( "-k", "--keep_zero_length", action="store_true", dest="keep_zero_length", default=False, help="Keep reads with zero length")
    ( options, args ) = parser.parse_args()
    
    if len ( args ) != 2:
        parser.error( "Need to specify an input file and an output file" )
    
    if options.window_size < 1:
        parser.error( 'You must specify a strictly positive window size' )
    
    if options.window_step < 1:
        parser.error( 'You must specify a strictly positive step size' )
    
    #determine an exhaustive list of window indexes that can be excluded from aggregation
    exclude_window_indexes = []
    last_exclude_indexes = []
    for exclude_count in range( min( options.exclude_count, options.window_size ) ):
        if last_exclude_indexes:
            new_exclude_indexes = []
            for exclude_list in last_exclude_indexes:
                for window_index in range( options.window_size ):
                    if window_index not in exclude_list:
                        new_exclude = sorted( exclude_list + [ window_index ] )
                        if new_exclude not in exclude_window_indexes + new_exclude_indexes:
                            new_exclude_indexes.append( new_exclude )
            exclude_window_indexes += new_exclude_indexes
            last_exclude_indexes = new_exclude_indexes
        else:
            for window_index in range( options.window_size ):
                last_exclude_indexes.append( [ window_index ] )
            exclude_window_indexes = list( last_exclude_indexes )
    
    out = fastqWriter( open( args[1], 'wb' ), format = options.format )
    action = ACTION_METHODS[ options.aggregation_action ]
    
    num_reads = None
    num_reads_excluded = 0
    for num_reads, fastq_read in enumerate( fastqReader( open( args[0] ), format = options.format ) ):
        for trim_end in options.trim_ends:
            quality_list = fastq_read.get_decimal_quality_scores()
            if trim_end == '5':
                lwindow_position = 0 #left position of window
                while True:
                    if lwindow_position >= len( quality_list ):
                        fastq_read.sequence = ''
                        fastq_read.quality = ''
                        break
                    if exclude_and_compare( action, quality_list[ lwindow_position:lwindow_position + options.window_size ], options.score_comparison, options.quality_score, exclude_window_indexes ):
                        fastq_read = fastq_read.slice( lwindow_position, None )
                        break
                    lwindow_position += options.window_step
            else:
                rwindow_position = len( quality_list ) #right position of window
                while True:
                    lwindow_position = rwindow_position - options.window_size #left position of window
                    if rwindow_position <= 0 or lwindow_position < 0:
                        fastq_read.sequence = ''
                        fastq_read.quality = ''
                        break
                    if exclude_and_compare( action, quality_list[ lwindow_position:rwindow_position ], options.score_comparison, options.quality_score, exclude_window_indexes ):
                        fastq_read = fastq_read.slice( None, rwindow_position )
                        break
                    rwindow_position -= options.window_step
        if options.keep_zero_length or len( fastq_read ):
            out.write( fastq_read )
        else:
            num_reads_excluded += 1
    out.close()
    if num_reads is None:
        print "No valid FASTQ reads could be processed."
    else:
        print "%i FASTQ reads were processed." % ( num_reads + 1 )
    if num_reads_excluded:
        print "%i reads of zero length were excluded from the output." % num_reads_excluded

if __name__ == "__main__": main()
