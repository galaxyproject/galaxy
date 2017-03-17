import hashlib
import json
import logging

from galaxy.exceptions import ObjectHashExistsException

from uuid import uuid4

from .base import ModelManager

from galaxy import exceptions
from galaxy import model

log = logging.getLogger(__name__)


class DynamicToolManager(ModelManager):
    """ Manages dynamic tools stored in Galaxy's database.
    """
    model_class = model.DynamicTool

    def __init__(self, app):
        super(DynamicToolManager, self).__init__(app)

    def get_tool_by_uuid(self, uuid):
        dynamic_tool = self._one_or_none(
            self.query().filter(self.model_class.uuid == uuid)
        )
        return dynamic_tool

    def get_tool_by_id_or_hash(self, id_or_hash):
        dynamic_tool = self._one_or_none(
            self.query().filter(self.model_class.tool_id == id_or_hash)
        )
        if dynamic_tool is None:
            dynamic_tool = self.get_tool_by_hash(id_or_hash)
        return dynamic_tool

    def get_tool_by_hash( self, tool_hash ):
        return self._one_or_none(
            self.query().filter(self.model_class.tool_hash == tool_hash)
        )

    def create_tool(self, tool_payload):
        if "representation" not in tool_payload:
            raise exceptions.ObjectAttributeMissingException(
                "A tool 'representation' is required."
            )

        representation = tool_payload["representation"]
        if "class" not in representation:
            raise exceptions.ObjectAttributeMissingException(
                "Current tool representations require 'class'."
            )

        tool_format = representation["class"]
        if tool_format == "GalaxyTool":
            uuid = tool_payload.get("uuid", None)
            if uuid is None:
                uuid = uuid4()

            tool_id = representation.get("id", None)
            if tool_id is None:
                tool_id = str(uuid)

            tool_version = representation.get("version", None)
            tool_hash = build_tool_hash(representation)
            value = representation
        elif tool_format in ["CommandLineTool", "ExpressionTool"]:
            # CWL tools
            uuid = None
            tool_id = representation.get("id", None)
            tool_version = representation.get("version", None)
            tool_hash = build_tool_hash(representation)
            value = representation
        else:
            raise Exception("Unknown tool type encountered.")
        # TODO: enforce via DB constraint and catch appropriate
        # exception.
        existing_tool = self.get_tool_by_hash( tool_hash )
        if existing_tool is not None:
            raise ObjectHashExistsException(existing_tool.id)
        dynamic_tool = self.create(
            tool_format=tool_format,
            tool_id=tool_id,
            tool_version=tool_version,
            tool_hash=tool_hash,
            uuid=uuid,
            value=value,
        )
        self.app.toolbox.load_dynamic_tool( dynamic_tool )
        return dynamic_tool

    def list_tools(self, active=True):
        return self.query().filter(active=active)


def build_tool_hash(as_dict):
    # http://stackoverflow.com/a/22003440
    as_str = json.dumps(as_dict, sort_keys=True )

    m = hashlib.sha256()
    m.update(as_str)
    hash = m.hexdigest()
    return hash
