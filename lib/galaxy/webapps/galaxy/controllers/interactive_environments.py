"""
API check for whether the current session's interactive environment launch is ready
"""
import logging

from galaxy.web import expose, json
from galaxy.web.base.controller import BaseUIController


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
        if not proxy_map.container_interface:
            # not using the new containers interface
            return True

        try:
            interface = self.app.containers[proxy_map.container_interface]
        except KeyError:
            log.error('Invalid container interface key: %s', proxy_map.container_interface)
            return None
        container = interface.get_container(proxy_map.container_ids[0])
        if not proxy_map.port > 0:
            # a negative port means it failed to be determined at launch time; the negated negative port is the
            # container port
            log.debug("Container %s (%s) mapping for port %s is not set in the proxy, attempting to get port mapping "
                      "now", container.name, container.id, -proxy_map.port)
            mapping = container.map_port(-proxy_map.port)
            if mapping:
                log.info("Container %s (%s) port %s accessible at: %s:%s", container.name, container.id,
                         -proxy_map.port, mapping.hostaddr, mapping.hostport)
                self.app.proxy_manager.update_proxy(trans, host=mapping.hostaddr, port=mapping.hostport)
            else:
                log.warning("Container %s (%s) mapping for port %s cannot be determined!", container.name, container.id,
                            -proxy_map.port)
                return False
        return container.is_ready()
