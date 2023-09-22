import logging
from typing import (
    Dict,
    NamedTuple,
    Optional,
)

from galaxy.util import parse_xml_string
from galaxy.util.path import StrPath
from galaxy.util.tool_shed import common_util
from galaxy.util.tool_shed.xml_util import parse_xml

log = logging.getLogger(__name__)

DEFAULT_TOOL_SHED_URL = "https://toolshed.g2.bx.psu.edu/"
DEFAULT_TOOL_SHED_NAME = "Galaxy Main Tool Shed"
DEFAULT_TOOL_SHEDS_CONF_XML = f"""<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="{DEFAULT_TOOL_SHED_NAME}" url="{DEFAULT_TOOL_SHED_URL}"/>
</tool_sheds>
"""


class AUTH_TUPLE(NamedTuple):
    username: str
    password: str


class Registry:
    tool_sheds: Dict[str, str]
    tool_sheds_auth: Dict[str, Optional[AUTH_TUPLE]]

    def __init__(self, config: Optional[StrPath] = None):
        self.tool_sheds = {}
        self.tool_sheds_auth = {}
        if config:
            # Parse tool_sheds_conf.xml
            tree, error_message = parse_xml(config)
            if tree is None:
                log.warning(f"Unable to load references to tool sheds defined in file {str(config)}")
                return
            root = tree.getroot()
        else:
            root = parse_xml_string(DEFAULT_TOOL_SHEDS_CONF_XML)
            config = "internal default config"
        log.debug(f"Loading references to tool sheds from {config}")
        for elem in root.findall("tool_shed"):
            try:
                name = elem.get("name", None)
                url = elem.get("url", None)
                username = elem.get("user", None)
                password = elem.get("pass", None)
                if name and url:
                    self.tool_sheds[name] = url
                    self.tool_sheds_auth[name] = None
                    log.debug(f"Loaded reference to tool shed: {name}")
                if name and url and username and password:
                    self.tool_sheds_auth[name] = AUTH_TUPLE(username, password)
            except Exception as e:
                log.warning(f'Error loading reference to tool shed "{name}", problem: {str(e)}')

    def url_auth(self, url: str) -> Optional[AUTH_TUPLE]:
        """
        If the tool shed is using external auth, the client to the tool shed must authenticate to that
        as well.  This provides access to the six.moves.urllib.request.HTTPPasswordMgrWithdefaultRealm() object for the
        url passed in.

        Following more what galaxy.demo_sequencer.controllers.common does might be more appropriate at
        some stage...
        """
        shed_name = self._shed_name_for_url(url)
        if shed_name is not None:
            return self.tool_sheds_auth[shed_name]
        else:
            log.debug(f"Invalid url '{str(url)}' received by tool shed registry's url_auth method.")
            return None

    def _shed_name_for_url(self, url: str) -> Optional[str]:
        url_sans_protocol = common_util.remove_protocol_from_tool_shed_url(url)
        for shed_name, shed_url in self.tool_sheds.items():
            shed_url_sans_protocol = common_util.remove_protocol_from_tool_shed_url(shed_url)
            if url_sans_protocol.startswith(shed_url_sans_protocol):
                return shed_name
        return None

    def get_tool_shed_url(self, tool_shed: str) -> Optional[str]:
        """
        The value of tool_shed is something like: toolshed.g2.bx.psu.edu.  We need the URL to this tool shed, which is
        something like: http://toolshed.g2.bx.psu.edu/
        """
        cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
        for shed_url in self.tool_sheds.values():
            if shed_url.find(cleaned_tool_shed) >= 0:
                if shed_url.endswith("/"):
                    shed_url = shed_url.rstrip("/")
                return shed_url
        # The tool shed from which the repository was originally installed must no longer be configured in tool_sheds_conf.xml.
        return None
