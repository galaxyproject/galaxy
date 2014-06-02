import collections
import os

from xml.etree import ElementTree

from galaxy.util.submodules import submodules
from galaxy import util

from ..metrics import formatting

import logging
log = logging.getLogger( __name__ )


DEFAULT_FORMATTER = formatting.JobMetricFormatter()


class JobMetrics( object ):

    def __init__( self, conf_file=None, **kwargs ):
        """
        """
        self.plugin_classes = self.__plugins_dict()
        self.default_job_instrumenter = JobInstrumenter.from_file( self.plugin_classes, conf_file, **kwargs )
        self.job_instrumenters = collections.defaultdict( lambda: self.default_job_instrumenter )

    def format( self, plugin, key, value ):
        if plugin in self.plugin_classes:
            plugin_class = self.plugin_classes[ plugin ]
            formatter = plugin_class.formatter
        else:
            formatter = DEFAULT_FORMATTER
        return formatter.format( key, value )

    def set_destination_conf_file( self, destination_id, conf_file ):
        instrumenter = JobInstrumenter.from_file( self.plugin_classes, conf_file )
        self.set_destination_instrumenter( destination_id, instrumenter )

    def set_destination_conf_element( self, destination_id, element ):
        instrumenter = JobInstrumenter( self.plugin_classes, element )
        self.set_destination_instrumenter( destination_id, instrumenter )

    def set_destination_instrumenter( self, destination_id, job_instrumenter=None ):
        if job_instrumenter is None:
            job_instrumenter = NULL_JOB_INSTRUMENTER
        self.job_instrumenters[ destination_id ] = job_instrumenter

    def collect_properties( self, destination_id, job_id, job_directory ):
        return self.job_instrumenters[ destination_id ].collect_properties( job_id, job_directory )

    def __plugins_dict( self ):
        plugin_dict = {}
        for plugin_module in self.__plugin_modules():
            for clazz in plugin_module.__all__:
                plugin_type = getattr( clazz, 'plugin_type', None )
                if plugin_type:
                    plugin_dict[ plugin_type ] = clazz
        return plugin_dict

    def __plugin_modules( self ):
        import galaxy.jobs.metrics.instrumenters
        return submodules( galaxy.jobs.metrics.instrumenters )


class NullJobInstrumenter( object ):

    def pre_execute_commands( self, job_directory ):
        return None

    def post_execute_commands( self, job_directory ):
        return None

    def collect_properties( self, job_id, job_directory ):
        return {}

NULL_JOB_INSTRUMENTER = NullJobInstrumenter()


class JobInstrumenter( object ):

    def __init__( self, plugin_classes, metrics_element, **kwargs ):
        self.extra_kwargs = kwargs
        self.plugin_classes = plugin_classes
        self.plugins = self.__plugins_for_element( metrics_element )

    def pre_execute_commands( self, job_directory ):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.pre_execute_instrument( job_directory )
                if plugin_commands:
                    commands.extend( util.listify( plugin_commands ) )
            except Exception:
                log.exception( "Failed to generate pre-execute commands for plugin %s" % plugin )
        return "\n".join( [ c for c in commands if c ] )

    def post_execute_commands( self, job_directory ):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.post_execute_instrument( job_directory )
                if plugin_commands:
                    commands.extend( util.listify( plugin_commands ) )
            except Exception:
                log.exception( "Failed to generate post-execute commands for plugin %s" % plugin )
        return "\n".join( [ c for c in commands if c ] )

    def collect_properties( self, job_id, job_directory ):
        per_plugin_properites = {}
        for plugin in self.plugins:
            try:
                properties = plugin.job_properties( job_id, job_directory )
                if properties:
                    per_plugin_properites[ plugin.plugin_type ] = properties
            except Exception:
                log.exception( "Failed to collect job properties for plugin %s" % plugin )
        return per_plugin_properites

    def __plugins_for_element( self, plugins_element ):
        plugins = []
        for plugin_element in plugins_element.getchildren():
            plugin_type = plugin_element.tag
            plugin_kwds = dict( plugin_element.items() )
            plugin_kwds.update( self.extra_kwargs )
            plugin = self.plugin_classes[ plugin_type ]( **plugin_kwds )
            plugins.append( plugin )
        return plugins

    @staticmethod
    def from_file( plugin_classes, conf_file, **kwargs ):
        if not conf_file or not os.path.exists( conf_file ):
            return NULL_JOB_INSTRUMENTER
        plugins_element = ElementTree.parse( conf_file ).getroot()
        return JobInstrumenter( plugin_classes, plugins_element, **kwargs )
