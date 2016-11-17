"""This module describes :class:`CollectlCli` - an abstraction for building collectl command lines."""
import logging
import subprocess
from string import Template

log = logging.getLogger( __name__ )

COMMAND_LINE_TEMPLATE = Template(
    "$collectl_path $destination_arg $mode_arg $subsystems_arg $interval_arg $procfilt_arg $flush_arg $sep_arg"
)
MODE_RECORD = "record"
MODE_PLAYBACK = "playback"


class CollectlCli( object ):
    """
    Abstraction over (some of) the command-line arguments of collectl.
    Ideally this will be useful for building up command line arguments for
    remote execution as well as runnning directly on local host.

    This is meant to be a fairly generic utility - for interfacing with
    collectl CLI - logic more directly related to the Galaxy job metric plugin
    plugin should be placed in other modules.

    **Keyword Arguments:**

    ``collectl_path``
        Path to collectl executable (defaults to collectl - i.e.
        search the PATH).

    ``playback_path`` (defaults to ``None``)
        If this is ``None``, collectl will run in
        record mode, else it will playback specified file.

    **Playback Mode Options:**

    ``sep``
        Separator used in playback mode (set to 9 to produce tsv)
        (defaults to None).

    **Record Mode Options** (some of these may work in playback mode also)

    ``destination_path``
        Location of path files to write to (defaults to None
        and collectl will just use cwd). Really this is just to prefix -
        collectl will append hostname and datetime to file.
    ``interval``
        Setup polling interval (secs) for most subsystems (defaults
        to None and when unspecified collectl will use default of 1 second).
    ``interval2``
        Setup polling interval (secs) for process information
        (defaults to None and when unspecified collectl will use default to
        60 seconds).
    ``interval3``
        Setup polling interval (secs) for environment information
        (defaults to None and when unspecified collectl will use default to
        300 seconds).
    ``procfilt``
        Optional argument to procfilt. (defaults to None).
    ``flush``
        Optional flush interval (defaults to None).
    """

    def __init__( self, **kwargs ):
        command_args = {}
        command_args[ "collectl_path" ] = kwargs.get( "collectl_path", "collectl" )
        playback_path = kwargs.get( "playback_path", None )
        self.mode = MODE_RECORD if not playback_path else MODE_PLAYBACK
        if self.mode == MODE_RECORD:
            mode_arg = ""
        elif self.mode == MODE_PLAYBACK:
            mode_arg = "-P -p '%s'" % playback_path
        else:
            raise Exception( "Invalid mode supplied to CollectlCli - %s" % self.mode )
        command_args[ "mode_arg" ] = mode_arg
        command_args[ "interval_arg" ] = self.__interval_arg( kwargs )
        destination = kwargs.get( "destination_path", None )
        if destination:
            destination_arg = "-f '%s'" % destination
        else:
            destination_arg = ""
        command_args[ "destination_arg" ] = destination_arg
        procfilt = kwargs.get( "procfilt", None )
        command_args[ "procfilt_arg" ] = "" if not procfilt else "--procfilt %s" % procfilt
        command_args[ "subsystems_arg" ] = self.__subsystems_arg( kwargs.get( "subsystems", [] ) )
        flush = kwargs.get( "flush", None )
        command_args[ "flush_arg"] = "--flush %s" % flush if flush else ""
        sep = kwargs.get( "sep", None )
        command_args[ "sep_arg" ] = "--sep=%s" % sep if sep else ""

        self.command_args = command_args

    def __subsystems_arg( self, subsystems ):
        if subsystems:
            return "-s%s" % "".join( [ s.command_line_arg for s in subsystems ] )
        else:
            return ""

    def __interval_arg( self, kwargs ):
        if self.mode != MODE_RECORD:
            return ""

        interval = kwargs.get( "interval", None )
        if not interval:
            return ""

        self.__validate_interval_arg( interval )
        interval_arg = "-i %s" % interval
        interval2 = kwargs.get( "interval2", None )
        if not interval2:
            return interval_arg
        self.__validate_interval_arg( interval2, multiple_of=int( interval ) )
        interval_arg = "%s:%s" % ( interval_arg, interval2 )

        interval3 = kwargs.get( "interval3", None )
        if not interval3:
            return interval_arg
        self.__validate_interval_arg( interval3, multiple_of=int( interval ) )
        interval_arg = "%s:%s" % ( interval_arg, interval3 )
        return interval_arg

    def __validate_interval_arg( self, value, multiple_of=None ):
        if value and not str(value).isdigit():
            raise Exception( "Invalid interval argument supplied, must be integer %s" % value )
        if multiple_of:
            if int( value ) % multiple_of != 0:
                raise Exception( "Invalid interval argument supplied, must multiple of %s" % multiple_of )

    def build_command_line( self ):
        return COMMAND_LINE_TEMPLATE.substitute( **self.command_args )

    def run( self, stdout=subprocess.PIPE, stderr=subprocess.PIPE ):
        command_line = self.build_command_line()
        log.info( "Executing %s" % command_line )
        proc = subprocess.Popen( command_line, shell=True, stdout=stdout, stderr=stderr )
        return_code = proc.wait()
        if return_code:
            raise Exception( "Problem running collectl command." )


__all__ = ( 'CollectlCli', )
