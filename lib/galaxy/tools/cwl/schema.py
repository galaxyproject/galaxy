from collections import namedtuple
import os

from six.moves.urllib.parse import urldefrag

from .cwltool_deps import (
    process,
    schema_salad,
    workflow,
)

ProcessDefinition = namedtuple("ProcessObject", ["process_object", "metadata"])


class SchemaLoader(object):

    def __init__(self, strict=True):
        self._strict = strict
        self._document_loader = None
        self._avsc_names = None

    def _lazy_init(self):
        if self._document_loader is not None:
            return

        document_loader, avsc_names, _ = process.get_schema()
        self._document_loader = document_loader
        self._avsc_names = avsc_names

        if isinstance(avsc_names, Exception):
            raise avsc_names

    def raw_object(self, path):
        self._lazy_init()
        self._document_loader.idx.clear()
        uri = "file://" + os.path.abspath(path)
        fileuri, _ = urldefrag(uri)
        return self._document_loader.fetch(fileuri)

    def process_definition(self, raw_object):
        self._lazy_init()
        process_object, metadata = schema_salad.schema.load_and_validate(
            self._document_loader,
            self._avsc_names,
            raw_object,
            self._strict,
        )
        return ProcessDefinition(process_object, metadata)

    def tool(self, **kwds):
        self._lazy_init()
        process_definition = kwds.get("process_definition", None)
        if process_definition is None:
            raw_object = kwds.get("raw_object", None)
            if raw_object is None:
                raw_object = self.raw_object(kwds["path"])
            process_definition = self.process_definition(raw_object)

        make_tool = kwds.get("make_tool", workflow.defaultMakeTool)
        tool = make_tool(
            process_definition.process_object,
            strict=self._strict,
            makeTool=make_tool,
            loader=self._document_loader,
            avsc_names=self._avsc_names,
        )
        if process_definition.metadata:
            metadata = process_definition.metadata
        else:
            metadata = {
                "$namespaces": tool.tool.get("$namespaces", {}),
                "$schemas": tool.tool.get("$schemas", [])
            }

        tool.metadata = metadata
        return tool

schema_loader = SchemaLoader()
