"""
API check for whether the current session's interactive environment launch is ready
"""
import logging

from galaxy.containers import build_container_interfaces
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

        container_interfaces = build_container_interfaces(
            self.app.config.containers_config_file,
            containers_conf=self.app.config.containers_conf,
        )
        try:
            interface = container_interfaces[proxy_map.container_interface]
        except KeyError:
            log.error('Invalid container interface key: %s', proxy_map.container_interface)
            return None
        container = interface.get_container(proxy_map.container_ids[0])
        return container.is_ready()
