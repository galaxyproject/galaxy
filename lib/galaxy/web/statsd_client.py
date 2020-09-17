try:
    import statsd
except ImportError:
    statsd = None


# TODO: optimize with two separate implementations around statsd_influxdb?
class GalaxyStatsdClient:

    def __init__(self,
                 statsd_host,
                 statsd_port,
                 statsd_prefix,
                 statsd_influxdb):
        if not statsd:
            raise ImportError("Statsd logging configured, but no statsd python module found. "
                           "Please install the python statsd module to use this functionality.")

        self.metric_infix = ''
        self.statsd_influxdb = statsd_influxdb
        if self.statsd_influxdb:
            statsd_prefix = statsd_prefix.strip(',')
        self.statsd_client = statsd.StatsClient(statsd_host, statsd_port, prefix=statsd_prefix)

    def timing(self, path, time, tags=None):
        infix = self._effective_infix(path, tags)
        self.statsd_client.timing(infix + path, time)

    def incr(self, path, n=1, tags=None):
        infix = self._effective_infix(path, tags)
        self.statsd_client.incr(infix + path, n)

    def _effective_infix(self, path, tags):
        tags = tags or {}
        if self.statsd_influxdb and tags:
            return ',' + ",".join("{}={}".format(k, v) for (k, v) in tags.items()) + ",path="
        if self.statsd_influxdb:
            return ',path='
        else:
            return ''
