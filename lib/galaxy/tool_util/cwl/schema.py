"""Abstraction around cwltool and related libraries for loading a CWL artifact."""
import os
from collections import namedtuple

from six.moves.urllib.parse import urldefrag

from .cwltool_deps import (
    ensure_cwltool_available,
    load_tool,
    LoadingContext,
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
        ensure_cwltool_available()
        from cwltool.load_tool import jobloaderctx
        return schema_salad.ref_resolver.Loader(jobloaderctx)

    def raw_process_reference(self, path):
        uri = "file://" + os.path.abspath(path)
        fileuri, _ = urldefrag(uri)
        return RawProcessReference(self.raw_document_loader.fetch(fileuri), uri)

    def raw_process_reference_for_object(self, object, uri=None):
        if uri is None:
            uri = "galaxy://"
        return RawProcessReference(object, uri)

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
        # cwl.workflow.defaultMakeTool() method was renamed to default_make_tool() in
        # https://github.com/common-workflow-language/cwltool/commit/886a6ac41c685f20d39e352f9c657e59f3312265
        try:
            default_make_tool = workflow.default_make_tool
        except AttributeError:
            default_make_tool = workflow.defaultMakeTool
        process_definition = kwds.get("process_definition", None)
        if process_definition is None:
            raw_process_reference = kwds.get("raw_process_reference", None)
            if raw_process_reference is None:
                raw_process_reference = self.raw_process_reference(kwds["path"])
            process_definition = self.process_definition(raw_process_reference)

        args = {"strict": self._strict}
        make_tool = kwds.get("make_tool", default_make_tool)
        if LoadingContext is not None:
            args["construct_tool_object"] = make_tool
            loading_context = LoadingContext(args)
            tool = load_tool.make_tool(
                process_definition.document_loader,
                process_definition.avsc_names,
                process_definition.metadata,
                process_definition.raw_process_reference.uri,
                loading_context,
            )
        else:
            tool = load_tool.make_tool(
                process_definition.document_loader,
                process_definition.avsc_names,
                process_definition.metadata,
                process_definition.raw_process_reference.uri,
                make_tool,
                args
            )
        return tool


schema_loader = SchemaLoader()
non_strict_schema_loader = SchemaLoader(strict=False)
