"""Abstraction around cwltool and related libraries for loading a CWL artifact."""
import os

from collections import namedtuple

from six.moves.urllib.parse import urldefrag

from .cwltool_deps import (
    ensure_cwltool_available,
    load_tool,
    schema_salad,
    workflow,
)

RawProcessReference = namedtuple("RawProcessReference", ["process_object", "uri"])
ProcessDefinition = namedtuple("ProcessDefinition", ["process_object", "metadata", "document_loader", "avsc_names", "raw_process_reference"])


class SchemaLoader(object):

    def __init__(self, strict=True):
        self._strict = strict
        self._raw_document_loader = None

    @property
    def raw_document_loader(self):
        if self._raw_document_loader is None:
            ensure_cwltool_available()
            self._raw_document_loader = schema_salad.ref_resolver.Loader({"cwl": "https://w3id.org/cwl/cwl#", "id": "@id"})

        return self._raw_document_loader

    def raw_process_reference(self, path):
        uri = "file://" + os.path.abspath(path)
        fileuri, _ = urldefrag(uri)
        return RawProcessReference(self.raw_document_loader.fetch(fileuri), uri)

    def process_definition(self, raw_reference):
        document_loader, avsc_names, process_object, metadata, uri = load_tool.validate_document(
            self.raw_document_loader,
            raw_reference.process_object,
            raw_reference.uri,
        )
        process_def = ProcessDefinition(
            process_object,
            metadata,
            document_loader,
            avsc_names,
            raw_reference,
        )
        return process_def

    def tool(self, **kwds):
        process_definition = kwds.get("process_definition", None)
        if process_definition is None:
            raw_process_reference = kwds.get("raw_process_reference", None)
            if raw_process_reference is None:
                raw_process_reference = self.raw_process_reference(kwds["path"])
            process_definition = self.process_definition(raw_process_reference)

        make_tool = kwds.get("make_tool", workflow.defaultMakeTool)
        tool = load_tool.make_tool(
            process_definition.document_loader,
            process_definition.avsc_names,
            process_definition.metadata,
            process_definition.raw_process_reference.uri,
            make_tool,
            {"strict": self._strict},
        )
        return tool

schema_loader = SchemaLoader()
