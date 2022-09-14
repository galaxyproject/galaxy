"""Utilities defining "Galaxy Flavored Markdown".

This is an extension of markdown designed to allow rendering Galaxy object
references.

The core "Galaxy Flavored Markdown" format should just reference objects
by encoded IDs - but preprocessing should allow for instance workflow objects
to be referenced relative to the workflow (inputs, outputs, steps, etc..) and
potential history flavor would allow objects to be referenced by HID. This
second idea is unimplemented, it is just an example of the general concept of
context specific processing.
"""
import abc
import base64
import codecs
import logging
import os
import re
import shutil
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Match,
    Optional,
)

import markdown

try:
    import weasyprint
except Exception:
    weasyprint = None

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    MalformedContents,
    ServerNotConfiguredForRequest,
)
from galaxy.managers.hdcas import HDCASerializer
from galaxy.managers.jobs import (
    JobManager,
    summarize_job_metrics,
    summarize_job_parameters,
)
from galaxy.model.item_attrs import get_item_annotation_str
from galaxy.model.orm.now import now
from galaxy.schema import PdfDocumentType
from galaxy.schema.tasks import GeneratePdfDownload
from galaxy.util.resources import resource_string
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.short_term_storage import (
    ShortTermStorageMonitor,
    storage_context,
)
from .markdown_parse import (
    GALAXY_MARKDOWN_FUNCTION_CALL_LINE,
    validate_galaxy_markdown,
)

log = logging.getLogger(__name__)

ARG_VAL_CAPTURED_REGEX = r"""(?:([\w_\-\|]+)|\"([^\"]+)\"|\'([^\']+)\')"""
OUTPUT_LABEL_PATTERN = re.compile(r"output=\s*%s\s*" % ARG_VAL_CAPTURED_REGEX)
INPUT_LABEL_PATTERN = re.compile(r"input=\s*%s\s*" % ARG_VAL_CAPTURED_REGEX)
STEP_LABEL_PATTERN = re.compile(r"step=\s*%s\s*" % ARG_VAL_CAPTURED_REGEX)
PATH_LABEL_PATTERN = re.compile(r"path=\s*%s\s*" % ARG_VAL_CAPTURED_REGEX)
# STEP_OUTPUT_LABEL_PATTERN = re.compile(r'step_output=([\w_\-]+)/([\w_\-]+)')
UNENCODED_ID_PATTERN = re.compile(
    r"(history_id|workflow_id|history_dataset_id|history_dataset_collection_id|job_id|invocation_id)=([\d]+)"
)
ENCODED_ID_PATTERN = re.compile(
    r"(history_id|workflow_id|history_dataset_id|history_dataset_collection_id|job_id|invocation_id)=([a-z0-9]+)"
)
INVOCATION_SECTION_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(r"```\s*galaxy\s*")
GALAXY_FENCED_BLOCK = re.compile(r"^```\s*galaxy\s*(.*?)^```", re.MULTILINE ^ re.DOTALL)
VALID_CONTAINER_START_PATTERN = re.compile(r"^```\s+[\w]+.*$")


def ready_galaxy_markdown_for_import(trans, external_galaxy_markdown):
    """Convert from encoded IDs to decoded numeric IDs for storing in the DB."""

    _validate(external_galaxy_markdown, internal=False)

    def _remap(container, line):
        id_match = re.search(ENCODED_ID_PATTERN, line)
        object_id = None
        if id_match:
            object_id = id_match.group(2)
            decoded_id = trans.security.decode_id(object_id)
            line = line.replace(id_match.group(), "%s=%d" % (id_match.group(1), decoded_id))
        return (line, False)

    internal_markdown = _remap_galaxy_markdown_calls(_remap, external_galaxy_markdown)
    return internal_markdown


class GalaxyInternalMarkdownDirectiveHandler(metaclass=abc.ABCMeta):
    def walk(self, trans, internal_galaxy_markdown):
        hda_manager = trans.app.hda_manager
        history_manager = trans.app.history_manager
        workflow_manager = trans.app.workflow_manager
        job_manager = JobManager(trans.app)
        collection_manager = trans.app.dataset_collection_manager

        def _check_object(object_id, line):
            if object_id is None:
                raise MalformedContents(f"Missing object identifier [{line}].")

        def _remap(container, line):
            id_match = re.search(UNENCODED_ID_PATTERN, line)
            object_id = None
            encoded_id = None
            if id_match:
                object_id = int(id_match.group(2))
                encoded_id = trans.security.encode_id(object_id)
                line = line.replace(id_match.group(), f"{id_match.group(1)}={encoded_id}")
            if container == "history_link":
                _check_object(object_id, line)
                history = history_manager.get_accessible(object_id, trans.user)
                rval = self.handle_history_link(line, history)
            elif container == "history_dataset_display":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_display(line, hda)
            elif container == "history_dataset_link":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_display(line, hda)
            elif container == "history_dataset_index":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_display(line, hda)
            elif container == "history_dataset_embedded":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_embedded(line, hda)
            elif container == "history_dataset_as_image":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_as_image(line, hda)
            elif container == "history_dataset_peek":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_peek(line, hda)
            elif container == "history_dataset_info":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_info(line, hda)
            elif container == "history_dataset_type":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_type(line, hda)
            elif container == "history_dataset_name":
                _check_object(object_id, line)
                hda = hda_manager.get_accessible(object_id, trans.user)
                rval = self.handle_dataset_name(line, hda)
            elif container == "workflow_display":
                stored_workflow = workflow_manager.get_stored_accessible_workflow(trans, encoded_id)
                rval = self.handle_workflow_display(line, stored_workflow)
            elif container == "history_dataset_collection_display":
                hdca = collection_manager.get_dataset_collection_instance(trans, "history", encoded_id)
                rval = self.handle_dataset_collection_display(line, hdca)
            elif container == "tool_stdout":
                job = job_manager.get_accessible_job(trans, object_id)
                rval = self.handle_tool_stdout(line, job)
            elif container == "tool_stderr":
                job = job_manager.get_accessible_job(trans, object_id)
                rval = self.handle_tool_stderr(line, job)
            elif container == "job_parameters":
                job = job_manager.get_accessible_job(trans, object_id)
                rval = self.handle_job_parameters(line, job)
            elif container == "job_metrics":
                job = job_manager.get_accessible_job(trans, object_id)
                rval = self.handle_job_metrics(line, job)
            elif container == "generate_galaxy_version":
                version = trans.app.config.version_major
                rval = self.handle_generate_galaxy_version(line, version)
            elif container == "generate_time":
                rval = self.handle_generate_time(line, now())
            elif container == "invocation_time":
                invocation = workflow_manager.get_invocation(trans, object_id)
                rval = self.handle_invocation_time(line, invocation)
            elif container == "visualization":
                rval = None
            else:
                raise MalformedContents(f"Unknown Galaxy Markdown directive encountered [{container}].")
            if rval is not None:
                return rval
            else:
                return (line, False)

        def _remap_container(container, line):
            try:
                return _remap(container, line)
            except Exception as e:
                return self.handle_error(container, line, str(e))

        export_markdown = _remap_galaxy_markdown_calls(_remap_container, internal_galaxy_markdown)
        return export_markdown

    @abc.abstractmethod
    def handle_history_link(self, line, history):
        pass

    @abc.abstractmethod
    def handle_dataset_display(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_as_image(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_peek(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_embedded(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_info(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_name(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_dataset_type(self, line, hda):
        pass

    @abc.abstractmethod
    def handle_workflow_display(self, line, stored_workflow):
        pass

    @abc.abstractmethod
    def handle_dataset_collection_display(self, line, hdca):
        pass

    @abc.abstractmethod
    def handle_tool_stdout(self, line, job):
        pass

    @abc.abstractmethod
    def handle_tool_stderr(self, line, job):
        pass

    @abc.abstractmethod
    def handle_job_metrics(self, line, job):
        pass

    @abc.abstractmethod
    def handle_job_parameters(self, line, job):
        pass

    @abc.abstractmethod
    def handle_generate_galaxy_version(self, line, galaxy_version):
        pass

    @abc.abstractmethod
    def handle_generate_time(self, line, date):
        pass

    @abc.abstractmethod
    def handle_invocation_time(self, line, date):
        pass

    @abc.abstractmethod
    def handle_error(self, container, line, error):
        pass


class ReadyForExportMarkdownDirectiveHandler(GalaxyInternalMarkdownDirectiveHandler):
    def __init__(self, trans, extra_rendering_data=None):
        extra_rendering_data = extra_rendering_data or {}
        self.trans = trans
        self.extra_rendering_data = extra_rendering_data

    def ensure_rendering_data_for(self, object_type, obj):
        encoded_id = self.trans.security.encode_id(obj.id)
        if object_type not in self.extra_rendering_data:
            self.extra_rendering_data[object_type] = {}
        object_type_data = self.extra_rendering_data[object_type]
        if encoded_id not in object_type_data:
            object_type_data[encoded_id] = {}
        return object_type_data[encoded_id]

    def extend_history_dataset_rendering_data(self, obj, key, val, default_val):
        self.ensure_rendering_data_for("history_datasets", obj)[key] = val or default_val

    def handle_dataset_display(self, line, hda):
        self.handle_dataset_name(line, hda)
        self.handle_dataset_type(line, hda)

    def handle_dataset_embedded(self, line, hda):
        self.handle_dataset_name(line, hda)

    def handle_dataset_peek(self, line, hda):
        self.extend_history_dataset_rendering_data(hda, "peek", hda.peek, "*No Dataset Peek Available*")

    def handle_dataset_info(self, line, hda):
        self.extend_history_dataset_rendering_data(hda, "info", hda.info, "*No Dataset Info Available*")

    def handle_workflow_display(self, line, stored_workflow):
        self.ensure_rendering_data_for("workflows", stored_workflow)["name"] = stored_workflow.name

    def handle_dataset_collection_display(self, line, hdca):
        hdca_serializer = HDCASerializer(self.trans.app)
        hdca_view = hdca_serializer.serialize_to_view(hdca, user=self.trans.user, trans=self.trans, view="summary")
        self.ensure_rendering_data_for("history_dataset_collections", hdca).update(hdca_view)

    def handle_tool_stdout(self, line, job):
        self.ensure_rendering_data_for("jobs", job)["tool_stdout"] = job.tool_stdout or "*No Standard Output Available*"

    def handle_tool_stderr(self, line, job):
        self.ensure_rendering_data_for("jobs", job)["tool_stderr"] = job.tool_stderr or "*No Standard Error Available*"

    def handle_history_link(self, line, history):
        self.ensure_rendering_data_for("histories", history)["name"] = history.name

    # Following three cases - the client side widgets have everything they need
    # from the encoded ID. Don't implement a default on the base class though because
    # it is good to force both Client and PDF/HTML export to deal with each new directive
    # explicitly.
    def handle_dataset_as_image(self, line, hda):
        pass

    def handle_job_metrics(self, line, job):
        pass

    def handle_job_parameters(self, line, job):
        pass

    def handle_generate_galaxy_version(self, line, generate_version):
        pass

    def handle_generate_time(self, line, generate_time):
        pass

    def handle_invocation_time(self, line, invocation):
        self.ensure_rendering_data_for("invocations", invocation)["create_time"] = invocation.create_time.isoformat()

    def handle_dataset_type(self, line, hda):
        self.extend_history_dataset_rendering_data(hda, "ext", hda.ext, "*Unknown dataset type*")

    def handle_dataset_name(self, line, hda):
        self.extend_history_dataset_rendering_data(hda, "name", hda.name, "*Unknown dataset name*")

    def handle_error(self, container, line, error):
        if "errors" not in self.extra_rendering_data:
            self.extra_rendering_data["errors"] = []
        self.extra_rendering_data["errors"].append(
            {
                "error": error,
                "line": line,
                "container": container,
            }
        )
        return (line, False)


def ready_galaxy_markdown_for_export(trans, internal_galaxy_markdown):
    """Fill in details needed to render Galaxy flavored markdown.

    Take it from a minimal internal version to an externally render-able version
    with more details populated and actual IDs replaced with encoded IDs to render
    external links. Return expanded markdown and extra data useful for rendering
    custom container tags.
    """
    extra_rendering_data = {
        "generate_time": now().isoformat(),
        "generate_version": trans.app.config.version_major,
    }
    # Walk Galaxy directives inside the Galaxy Markdown and collect dict-ified data
    # needed to render this efficiently.
    directive_handler = ReadyForExportMarkdownDirectiveHandler(trans, extra_rendering_data)
    export_markdown = directive_handler.walk(trans, internal_galaxy_markdown)
    return export_markdown, extra_rendering_data


class ToBasicMarkdownDirectiveHandler(GalaxyInternalMarkdownDirectiveHandler):
    def __init__(self, trans, markdown_formatting_helpers):
        self.trans = trans
        self.markdown_formatting_helpers = markdown_formatting_helpers

    def handle_dataset_display(self, line, hda):
        name = hda.name or ""
        markdown = "---\n"
        markdown += f"**Dataset:** {name}\n\n"
        markdown += self._display_dataset_content(hda)
        markdown += "\n---\n"
        return (markdown, True)

    def handle_dataset_embedded(self, line, hda):
        datatype = hda.datatype
        markdown = ""
        # subtly different than below since no Contents: prefix and new lines and such.
        if datatype is None:
            markdown += "*cannot display - cannot format unknown datatype*\n\n"
        else:
            markdown += datatype.display_as_markdown(hda, self.markdown_formatting_helpers)
        return (markdown, True)

    def _display_dataset_content(self, hda, header="Contents"):
        datatype = hda.datatype
        markdown = ""
        if datatype is None:
            markdown += f"**{header}:** *cannot display - cannot format unknown datatype*\n\n"
        else:
            markdown += f"**{header}:**\n"
            markdown += datatype.display_as_markdown(hda, self.markdown_formatting_helpers)
        return markdown

    def handle_dataset_as_image(self, line, hda):
        dataset = hda.dataset
        name = hda.name or ""
        path_match = re.search(PATH_LABEL_PATTERN, line)

        if path_match:
            filepath = path_match.group(2)
            file = os.path.join(hda.extra_files_path, filepath)
        else:
            file = dataset.file_name

        with open(file, "rb") as f:
            base64_image_data = base64.b64encode(f.read()).decode("utf-8")
        rval = (f"![{name}](data:image/png;base64,{base64_image_data})", True)
        return rval

    def handle_history_link(self, line, history):
        if history:
            content = self.markdown_formatting_helpers.literal_via_fence(history.name)
        else:
            content = "*No History available*"
        return (content, True)

    def handle_dataset_peek(self, line, hda):
        if hda.peek:
            content = self.markdown_formatting_helpers.literal_via_fence(hda.peek)
        else:
            content = "*No Dataset Peek Available*"
        return (content, True)

    def handle_dataset_info(self, line, hda):
        if hda.info:
            content = self.markdown_formatting_helpers.literal_via_fence(hda.info)
        else:
            content = "*No Dataset Info Available*"
        return (content, True)

    def handle_workflow_display(self, line, stored_workflow):
        # workflows/display.mako as markdown... meh...
        markdown = "---\n"
        markdown += f"**Workflow:** {stored_workflow.name}\n\n"
        markdown += "**Steps:**\n\n"
        markdown += "|Step|Annotation|\n"
        markdown += "|----|----------|\n"
        # Pass two should add tool information, labels, etc.. but
        # it requires module_injector and such.
        for order_index, step in enumerate(stored_workflow.latest_workflow.steps):
            annotation = get_item_annotation_str(self.trans.sa_session, self.trans.user, step) or ""
            markdown += "|{}|{}|\n".format(step.label or "Step %d" % (order_index + 1), annotation)
        markdown += "\n---\n"
        return (markdown, True)

    def handle_dataset_collection_display(self, line, hdca):
        name = hdca.name or ""
        # put it in a list to hack around no nonlocal on Python 2.
        markdown_wrapper = [f"**Dataset Collection:** {name}\n\n"]

        def walk_elements(collection, element_prefix=""):
            if ":" in collection.collection_type:
                for element in collection.elements:
                    walk_elements(element.child_collection, f"{element_prefix + element.element_identifier}:")
            else:
                for element in collection.elements:
                    markdown_wrapper[0] += f"**Element:** {element_prefix}{element.element_identifier}\n\n"
                    markdown_wrapper[0] += self._display_dataset_content(element.hda, header="Element Contents")

        walk_elements(hdca.collection)
        markdown = f"---\n{markdown_wrapper[0]}\n---\n"
        return (markdown, True)

    def handle_tool_stdout(self, line, job):
        stdout = job.tool_stdout or "*No Standard Output Available*"
        return (f"**Standard Output:** {stdout}", True)

    def handle_tool_stderr(self, line, job):
        stderr = job.tool_stderr or "*No Standard Error Available*"
        return (f"**Standard Error:** {stderr}", True)

    def handle_job_metrics(self, line, job):
        job_metrics = summarize_job_metrics(self.trans, job)
        metrics_by_plugin: Dict[str, Dict[str, Any]] = {}
        for job_metric in job_metrics:
            plugin = job_metric["plugin"]
            if plugin not in metrics_by_plugin:
                metrics_by_plugin[plugin] = {}
            metrics_by_plugin[plugin][job_metric["title"]] = job_metric["value"]
        markdown = ""
        for metric_plugin, metrics_for_plugin in metrics_by_plugin.items():
            markdown += f"**{metric_plugin}**\n\n"
            markdown += "|   |   |\n|---|--|\n"
            for title, value in metrics_for_plugin.items():
                markdown += f"| {title} | {value} |\n"
        return (markdown, True)

    def handle_job_parameters(self, line, job):
        markdown = """
| Input Parameter | Value |
|-----------------|-------|
"""
        parameters = summarize_job_parameters(self.trans, job)["parameters"]
        for parameter in parameters:
            markdown += "| "
            depth = parameter["depth"]
            if depth > 1:
                markdown += f"{'>' * (parameter['depth'] - 1)} "
            markdown += parameter["text"]
            markdown += " | "
            value = parameter["value"]
            if isinstance(value, list):
                markdown += ", ".join(f"{p['hid']}: {p['name']}" for p in value)
            else:
                markdown += value
            markdown += " |\n"

        return (markdown, True)

    def handle_generate_galaxy_version(self, line, generate_version):
        if generate_version:
            content = self.markdown_formatting_helpers.literal_via_fence(generate_version)
        else:
            content = "*No Galaxy Version Available*"
        return (content, True)

    def handle_generate_time(self, line, generate_time):
        content = self.markdown_formatting_helpers.literal_via_fence(generate_time.isoformat())
        return (content, True)

    def handle_invocation_time(self, line, invocation):
        content = self.markdown_formatting_helpers.literal_via_fence(invocation.create_time.isoformat())
        return (content, True)

    def handle_dataset_name(self, line, hda):
        if hda.name:
            content = self.markdown_formatting_helpers.literal_via_fence(hda.name)
        else:
            content = "*No Dataset Name Available*"
        return (content, True)

    def handle_dataset_type(self, line, hda):
        if hda.ext:
            content = self.markdown_formatting_helpers.literal_via_fence(hda.ext)
        else:
            content = "*No Dataset Type Available*"
        return (content, True)

    def handle_error(self, container, line, error):
        return (line, False)


class MarkdownFormatHelpers:
    """Inject common markdown formatting helpers for per-datatype rendering."""

    @staticmethod
    def literal_via_fence(content):
        return "\n%s\n" % "\n".join(f"    {line}" for line in content.splitlines())

    @staticmethod
    def indicate_data_truncated():
        return "\n**Warning:** The above data has been truncated to be embedded in this document.\n\n"

    @staticmethod
    def pre_formatted_contents(markdown):
        return f"<pre>{markdown}</pre>"


def to_basic_markdown(trans, internal_galaxy_markdown: str) -> str:
    """Replace Galaxy Markdown extensions with plain Markdown for PDF/HTML export."""
    markdown_formatting_helpers = MarkdownFormatHelpers()
    directive_handler = ToBasicMarkdownDirectiveHandler(trans, markdown_formatting_helpers)
    plain_markdown = directive_handler.walk(trans, internal_galaxy_markdown)
    return plain_markdown


def to_html(basic_markdown: str) -> str:
    # Allow data: urls so we can embed images.
    html = sanitize_html(markdown.markdown(basic_markdown, extensions=["tables"]), allow_data_urls=True)
    return html


def to_pdf_raw(basic_markdown: str, css_paths: Optional[List[str]] = None) -> bytes:
    """Convert RAW markdown with specified CSS paths into bytes of a PDF."""
    css_paths = css_paths or []
    as_html = to_html(basic_markdown)
    directory = tempfile.mkdtemp("gxmarkdown")
    index = os.path.join(directory, "index.html")
    try:
        output_file = codecs.open(index, "w", encoding="utf-8", errors="xmlcharrefreplace")
        output_file.write(as_html)
        output_file.close()
        html = weasyprint.HTML(filename=index)
        stylesheets = [weasyprint.CSS(string=resource_string(__package__, "markdown_export_base.css"))]
        for css_path in css_paths:
            with open(css_path) as f:
                css_content = f.read()
            css = weasyprint.CSS(string=css_content)
            stylesheets.append(css)
        return html.write_pdf(stylesheets=stylesheets)
    finally:
        shutil.rmtree(directory)


def weasyprint_available() -> bool:
    return weasyprint is not None


def _check_can_convert_to_pdf_or_raise():
    """Checks if the HTML to PDF converter is available."""
    if not weasyprint_available():
        raise ServerNotConfiguredForRequest("PDF conversion service not available.")


def internal_galaxy_markdown_to_pdf(trans, internal_galaxy_markdown: str, document_type: PdfDocumentType) -> bytes:
    _check_can_convert_to_pdf_or_raise()
    basic_markdown = to_basic_markdown(trans, internal_galaxy_markdown)
    config = trans.app.config
    return to_branded_pdf(basic_markdown, document_type, config)


def generate_branded_pdf(
    request: GeneratePdfDownload, config: GalaxyAppConfiguration, short_term_storage_monitor: ShortTermStorageMonitor
):
    with storage_context(request.short_term_storage_request_id, short_term_storage_monitor) as target:
        raw_contents = to_branded_pdf(
            request.basic_markdown,
            request.document_type,
            config,
        )
        with open(target.path, "wb") as f:
            f.write(raw_contents)


def to_branded_pdf(basic_markdown: str, document_type: PdfDocumentType, config: GalaxyAppConfiguration) -> bytes:
    document_type_prologue = getattr(config, f"markdown_export_prologue_{document_type}s", "") or ""
    document_type_epilogue = getattr(config, f"markdown_export_epilogue_{document_type}s", "") or ""
    general_prologue = config.markdown_export_prologue or ""
    general_epilogue = config.markdown_export_epilogue or ""
    effective_prologue = document_type_prologue or general_prologue
    effective_epilogue = document_type_epilogue or general_epilogue
    branded_markdown = effective_prologue + basic_markdown + effective_epilogue
    css_paths = []
    general_css_path = config.markdown_export_css
    document_type_css_path = getattr(config, f"markdown_export_css_{document_type}s", None)
    if general_css_path and os.path.exists(general_css_path):
        css_paths.append(general_css_path)
    if document_type_css_path and os.path.exists(document_type_css_path):
        css_paths.append(document_type_css_path)
    return to_pdf_raw(branded_markdown, css_paths=css_paths)


def resolve_invocation_markdown(trans, invocation, workflow_markdown):
    """Resolve invocation objects to convert markdown to 'internal' representation.

    Replace references to abstract workflow parts with actual galaxy object IDs corresponding
    to the actual executed workflow. For instance:

        convert output=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
        convert input=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
        convert step=name -to- job_id=<id>

    Also expand/convert workflow invocation specific container sections into actual Galaxy
    markdown - these containers include: invocation_inputs, invocation_outputs, invocation_workflow.
    Hopefully this list will be expanded to include invocation_qc.
    """
    # TODO: convert step outputs?
    # convert step_output=index/name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>

    def _section_remap(container, line):
        section_markdown = ""
        if container == "invocation_outputs":
            for output_assoc in invocation.output_associations:
                if not output_assoc.workflow_output.label:
                    continue

                if output_assoc.history_content_type == "dataset":
                    section_markdown += """#### Output Dataset: {}
```galaxy
history_dataset_display(output="{}")
```
""".format(
                        output_assoc.workflow_output.label, output_assoc.workflow_output.label
                    )
                else:
                    section_markdown += """#### Output Dataset Collection: {}
```galaxy
history_dataset_collection_display(output="{}")
```
""".format(
                        output_assoc.workflow_output.label, output_assoc.workflow_output.label
                    )
        elif container == "invocation_inputs":
            for input_assoc in invocation.input_associations:
                if not input_assoc.workflow_step.label:
                    continue

                if input_assoc.history_content_type == "dataset":
                    section_markdown += """#### Input Dataset: {}
```galaxy
history_dataset_display(input="{}")
```
""".format(
                        input_assoc.workflow_step.label, input_assoc.workflow_step.label
                    )
                else:
                    section_markdown += """#### Input Dataset Collection: {}
```galaxy
history_dataset_collection_display(input={})
```
""".format(
                        input_assoc.workflow_step.label, input_assoc.workflow_step.label
                    )
        else:
            return line, False
        return section_markdown, True

    def _remap(container, line):
        if container == "workflow_display":
            # TODO: this really should be workflow id not stored workflow id but the API
            # it consumes wants the stored id.
            return (f"workflow_display(workflow_id={invocation.workflow.stored_workflow.id})\n", False)
        if container == "history_link":
            return (f"history_link(history_id={invocation.history.id})\n", False)
        if container == "invocation_time":
            return (f"invocation_time(invocation_id={invocation.id})\n", False)
        ref_object_type = None
        output_match = re.search(OUTPUT_LABEL_PATTERN, line)
        input_match = re.search(INPUT_LABEL_PATTERN, line)
        step_match = re.search(STEP_LABEL_PATTERN, line)

        def find_non_empty_group(match):
            for group in match.groups():
                if group:
                    return group

        target_match: Optional[Match]
        ref_object: Optional[Any]
        if output_match:
            target_match = output_match
            name = find_non_empty_group(target_match)
            ref_object = invocation.get_output_object(name)
        elif input_match:
            target_match = input_match
            name = find_non_empty_group(target_match)
            ref_object = invocation.get_input_object(name)
        elif step_match:
            target_match = step_match
            name = find_non_empty_group(target_match)
            ref_object_type = "job"
            ref_object = invocation.step_invocation_for_label(name).job
        else:
            target_match = None
            ref_object = None
        if ref_object:
            assert target_match  # tell type system, this is set when ref_object is set
            if ref_object_type is None:
                if ref_object.history_content_type == "dataset":
                    ref_object_type = "history_dataset"
                else:
                    ref_object_type = "history_dataset_collection"
            line = line.replace(target_match.group(), f"{ref_object_type}_id={ref_object.id}")
        return (line, False)

    workflow_markdown = _remap_galaxy_markdown_calls(
        _section_remap,
        workflow_markdown,
    )
    galaxy_markdown = _remap_galaxy_markdown_calls(_remap, workflow_markdown)
    return galaxy_markdown


def _remap_galaxy_markdown_containers(func, markdown):
    new_markdown = markdown

    searching_from = 0
    while True:
        from_markdown = new_markdown[searching_from:]
        match = re.search(GALAXY_FENCED_BLOCK, from_markdown)
        if match is not None:
            replace = match.group(1)
            (replacement, whole_block) = func(replace)
            if whole_block:
                start_pos = match.start()
                end_pos = match.end()
            else:
                start_pos = match.start(1)
                end_pos = match.end(1)
            start_pos = start_pos + searching_from
            end_pos = end_pos + searching_from
            new_markdown = new_markdown[:start_pos] + replacement + new_markdown[end_pos:]
            searching_from = start_pos + len(replacement)
        else:
            break

    return new_markdown


def _remap_galaxy_markdown_calls(func, markdown):
    def _remap_container(container):
        matching_line = None
        for line in container.splitlines():
            if GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line):
                assert matching_line is None
                matching_line = line

        if matching_line:
            match = GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line)
            assert match  # already matched
            return func(match.group(1), f"{matching_line}\n")
        else:
            return (container, True)

    return _remap_galaxy_markdown_containers(_remap_container, markdown)


def _validate(*args, **kwds):
    """Light wrapper around validate_galaxy_markdown to throw galaxy exceptions instead of ValueError."""
    try:
        return validate_galaxy_markdown(*args, **kwds)
    except ValueError as e:
        raise MalformedContents(str(e))


__all__ = (
    "internal_galaxy_markdown_to_pdf",
    "ready_galaxy_markdown_for_export",
    "ready_galaxy_markdown_for_import",
    "resolve_invocation_markdown",
    "to_basic_markdown",
)
