"""
API check for whether the current session's interactive environment launch is ready
"""
from subprocess import Popen, PIPE

from galaxy.web import expose, json
from galaxy.web.base.controller import BaseUIController

import logging
log = logging.getLogger(__name__)


class InteractiveEnvironmentsController(BaseUIController):

    @expose
    @json
    def ready(self, trans, **kwd):
        """
        GET /interactive_environments/ready/

        Queries the GIE proxy IPC to determine whether the current user's session's GIE launch is ready

        :returns:   ``true`` if ready else ``false``
        :rtype:     boolean
        """
        proxy_map = self.app.proxy_manager.query_proxy(trans)
        if proxy_map.container_ids:
            command = proxy_map.docker_command.format(
                docker_args='ps --format {{{{.Status}}}} --filter id={container_id}'.format(
                    container_id=proxy_map.container_ids[0]))
            match_col = 0
            match_str = 'Up'
        elif proxy_map.service_ids:
            command = proxy_map.docker_command.format(
                docker_args='service ps --no-trunc {service_id}'.format(service_id=proxy_map.service_ids[0]))
            match_col = 5
            match_str = 'Running'
        else:
            raise Exception('Proxy map has neither container ids nor service ids stored')
        p = Popen(command, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            log.error( "%s\n%s" % (stdout, stderr) )
            return None
        else:
            return stdout.splitlines()[-1].strip().split()[match_col].startswith(match_str)
