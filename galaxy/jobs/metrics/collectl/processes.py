""" Modules will run collectl in playback mode and collect various process
statistics for a given pid's process and process ancestors.
"""
import collections
import csv
import logging
import sys
import tempfile

from galaxy import util

from ..collectl import stats

if sys.version_info > (3,):
    long = int

log = logging.getLogger( __name__ )

# Collectl process information cheat sheet:
#
# Record process information for current user.
# %  collectl -sZ -f./__instrument_collectl  -i 10:10 --procfilt U$USER
#
# TSV Replay of processing information in plottable mode...
#
# % collectl -sZ -P --sep=9 -p __instrument_collectl-jlaptop13-20140322-120919.raw.gz
#
# Has following columns:
#   Date   Time    PID     User    PR      PPID    THRD    S       VmSize  VmLck   VmRSS   VmData  VmStk   VmExe   VmLib   CPU       SysT    UsrT    PCT     AccumT  RKB     WKB     RKBC    WKBC    RSYS    WSYS    CNCL    MajF    MinF    Command
#

# Process data dumped one row per process per interval.
# http://collectl.sourceforge.net/Data-detail.html
PROCESS_COLUMNS = [
    "#Date",  # Date of interval - e.g. 20140322
    "Time",  # Time of interval - 12:18:58
    "PID",  # Process pid.
    "User",  # Process user.
    "PR",  # Priority of process.
    "PPID",  # Parent PID of process.
    "THRD",  # Thread???
    "S",  # Process state - S - Sleeping, D - Uninterruptable Sleep, R - Running, Z - Zombie or T - Stopped/Traced
    # Memory options - http://ewx.livejournal.com/579283.html
    "VmSize",
    "VmLck",
    "VmRSS",
    "VmData",
    "VmStk",
    "VmExe",
    "VmLib",
    "CPU",  # CPU number of process
    "SysT",  # Amount of system time consumed during interval
    "UsrT",  # Amount user time consumed during interval
    "PCT",  # Percentage of current interval consumed by task
    "AccumT",  # Total accumulated System and User time since the process began execution
    # kilobytes read/written - requires I/O level monitoring to be enabled in kernel.
    "RKB",  # kilobytes read by process - requires I/O monitoring in kernel
    "WKB",
    "RKBC",
    "WKBC",
    "RSYS",  # Number of read system calls
    "WSYS",  # Number of write system calls
    "CNCL",
    "MajF",  # Number of major page faults
    "MinF",  # Number of minor page faults
    "Command",  # Command executed
]

# Types of statistics this module can summarize
STATISTIC_TYPES = [ "max", "min", "sum", "count", "avg" ]

COLUMN_INDICES = dict( [ ( col, i ) for i, col in enumerate( PROCESS_COLUMNS ) ] )
PID_INDEX = COLUMN_INDICES[ "PID" ]
PARENT_PID_INDEX = COLUMN_INDICES[ "PPID" ]

DEFAULT_STATISTICS = [
    ("max", "VmSize"),
    ("avg", "VmSize"),
    ("max", "VmRSS"),
    ("avg", "VmRSS"),
    ("sum", "SysT"),
    ("sum", "UsrT"),
    ("max", "PCT"),
    ("avg", "PCT"),
    ("max", "AccumT"),
    ("sum", "RSYS"),
    ("sum", "WSYS"),
]


def parse_process_statistics( statistics ):
    """ Turn string or list of strings into list of tuples in format ( stat,
    resource ) where stat is a value from STATISTIC_TYPES and resource is a
    value from PROCESS_COLUMNS.
    """
    if statistics is None:
        statistics = DEFAULT_STATISTICS

    statistics = util.listify( statistics )
    statistics = map( _tuplize_statistic, statistics )
    # Check for validity...
    for statistic in statistics:
        if statistic[ 0 ] not in STATISTIC_TYPES:
            raise Exception( "Unknown statistic type encountered %s" % statistic[ 0 ] )
        if statistic[ 1 ] not in PROCESS_COLUMNS:
            raise Exception( "Unknown process column encountered %s" % statistic[ 1 ] )
    return statistics


def generate_process_statistics( collectl_playback_cli, pid, statistics=DEFAULT_STATISTICS ):
    """ Playback collectl file and generate summary statistics.
    """
    with tempfile.NamedTemporaryFile( ) as tmp_tsv:
        collectl_playback_cli.run( stdout=tmp_tsv )
        with open( tmp_tsv.name, "r" ) as tsv_file:
            return _read_process_statistics( tsv_file, pid, statistics )


def _read_process_statistics( tsv_file, pid, statistics ):
    process_summarizer = CollectlProcessSummarizer( pid, statistics )
    current_interval = None

    for row in csv.reader( tsv_file, dialect="excel-tab" ):
        if current_interval is None:
            for header, expected_header in zip( row, PROCESS_COLUMNS ):
                if header.lower() != expected_header.lower():
                    raise Exception( "Unknown header value encountered while processing collectl playback - %s" % header )

            # First row, check contains correct header.
            current_interval = CollectlProcessInterval()
            continue

        if current_interval.row_is_in( row ):
            current_interval.add_row( row )
        else:
            process_summarizer.handle_interval( current_interval )
            current_interval = CollectlProcessInterval()

    # Do we have unsummarized rows...
    if current_interval and current_interval.rows:
        process_summarizer.handle_interval( current_interval )

    return process_summarizer.get_statistics()


class CollectlProcessSummarizer( object ):

    def __init__( self, pid, statistics ):
        self.pid = pid
        self.statistics = statistics
        self.columns_of_interest = set( [ s[ 1 ] for s in statistics ] )
        self.tree_statistics = collections.defaultdict( stats.StatisticsTracker )
        self.process_accum_statistics = collections.defaultdict( stats.StatisticsTracker )
        self.interval_count = 0

    def handle_interval( self, interval ):
        self.interval_count += 1
        rows = self.__rows_for_process( interval.rows, self.pid )
        for column_name in self.columns_of_interest:
            column_index = COLUMN_INDICES[ column_name ]

            if column_name == "AccumT":
                # Should not sum this across pids each interval, sum max at end...
                for r in rows:
                    pid_seconds = self.__time_to_seconds( r[ column_index ] )
                    self.process_accum_statistics[ r[ PID_INDEX ] ].track( pid_seconds )
            else:
                # All other stastics should be summed across whole process tree
                # at each interval I guess.
                if column_name in [ "SysT", "UsrT", "PCT" ]:
                    to_num = float
                else:
                    to_num = long

                interval_stat = sum( to_num( r[ column_index ] ) for r in rows )
                self.tree_statistics[ column_name ].track( interval_stat )

    def get_statistics( self ):
        if self.interval_count == 0:
            return []

        computed_statistics = []
        for statistic in self.statistics:
            statistic_type, column = statistic
            if column == "AccumT":
                # Only thing that makes sense is sum
                if statistic_type != "max":
                    log.warning( "Only statistic max makes sense for AccumT" )
                    continue

                value = sum( [ v.max for v in self.process_accum_statistics.itervalues() ] )
            else:
                statistics_tracker = self.tree_statistics[ column ]
                value = getattr( statistics_tracker, statistic_type )

            computed_statistic = ( statistic, value )
            computed_statistics.append( computed_statistic )

        return computed_statistics

    def __rows_for_process( self, rows, pid ):
        process_rows = []
        pids = self.__all_child_pids( rows, pid )
        for row in rows:
            if row[ PID_INDEX ] in pids:
                process_rows.append( row )
        return process_rows

    def __all_child_pids( self, rows, pid ):
        pids_in_process_tree = set( [ str( self.pid ) ] )
        added = True
        while added:
            added = False
            for row in rows:
                pid = row[ PID_INDEX ]
                parent_pid = row[ PARENT_PID_INDEX ]
                if parent_pid in pids_in_process_tree and pid not in pids_in_process_tree:
                    pids_in_process_tree.add( pid )
                    added = True
        return pids_in_process_tree

    def __time_to_seconds( self, minutes_str ):
        parts = minutes_str.split( ":" )
        seconds = 0.0
        for i, val in enumerate( parts ):
            seconds += float(val) * ( 60 ** ( len( parts ) - ( i + 1 ) ) )
        return seconds


class CollectlProcessInterval( object ):
    """ Represent all rows in collectl playback file for given time slice with
    ability to filter out just rows corresponding to the process tree
    corresponding to a given pid.
    """

    def __init__( self ):
        self.rows = []

    def row_is_in( self, row ):
        if not self.rows:  # No rows, this row defines interval.
            return True
        first_row = self.rows[ 0 ]
        return first_row[ 0 ] == row[ 0 ] and first_row[ 1 ] == row[ 1 ]

    def add_row( self, row ):
        self.rows.append( row )


def _tuplize_statistic( statistic ):
    if not isinstance( statistic, tuple ):
        statistic_split = statistic.split( "_", 1 )
        statistic = ( statistic_split[ 0 ].lower(), statistic_split[ 1 ] )
    return statistic


__all__ = [ 'generate_process_statistics' ]
