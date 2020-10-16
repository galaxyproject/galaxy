"""The module describes the ``env`` job metrics plugin."""
import logging
import re

from . import InstrumentPlugin
from .. import formatting

log = logging.getLogger(__name__)


class EnvFormatter(formatting.JobMetricFormatter):
    pass


class EnvPlugin(InstrumentPlugin):
    """ Instrumentation plugin capable of recording all or specific environment
    variables for a job at runtime.
    """
    plugin_type = "env"
    formatter = EnvFormatter()

    def __init__(self, **kwargs):
        variables_str = kwargs.get("variables", None)
        if variables_str:
            variables = [v.strip() for v in variables_str.split(",")]
        else:
            variables = None
        self.variables = variables

    def pre_execute_instrument(self, job_directory):
        """ Use env to dump all environment variables to a file.
        """
        return "env > '%s'" % self.__env_file(job_directory)

    def post_execute_instrument(self, job_directory):
        return None

    def job_properties(self, job_id, job_directory):
        """ Recover environment variables dumped out on compute server and filter
        out specific variables if needed.
        """
        variables = self.variables

        properties = {}
        env_string = ''.join(open(self.__env_file(job_directory)).readlines())
        while env_string:
            # Check if the next lines contain a shell function.
            # We use '\n\}\n' as regex termination because shell
            # functions can be nested.
            # We use the non-greedy '.+?' because of re.DOTALL .
            m = re.match(r'([^=]+)=(\(\) \{.+?\n\})\n', env_string, re.DOTALL)
            if m is None:
                m = re.match('([^=]+)=(.*)\n', env_string)
            if m is None:
                # Some problem recording or reading back env output.
                message_template = "Problem parsing env metric output for job %s - properties will be incomplete"
                message = message_template % job_id
                log.debug(message)
                break
            (var, value) = m.groups()
            if not variables or var in variables:
                properties[var] = value
            env_string = env_string[m.end():]

        return properties

    def __env_file(self, job_directory):
        return self._instrument_file_path(job_directory, "vars")


__all__ = ('EnvPlugin', )
