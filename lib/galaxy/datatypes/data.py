import logging
import mimetypes
import os
import shutil
import string
import tempfile
from inspect import isclass
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    IO,
    Iterable,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from markupsafe import escape
from typing_extensions import Literal

from galaxy import util
from galaxy.datatypes.metadata import (
    MetadataElement,  # import directly to maintain ease of use in Datatype class definitions
)
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
    HasClearAssociatedFiles,
    HasCreatingJob,
    HasExt,
    HasExtraFilesAndMetadata,
    HasFileName,
    HasInfo,
    HasMetadata,
    HasName,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.exceptions import ObjectNotFound
from galaxy.util import (
    compression_utils,
    file_reader,
    FILENAME_VALID_CHARS,
    inflector,
    iter_start_of_line,
    unicodify,
    UNKNOWN,
)
from galaxy.util.bunch import Bunch
from galaxy.util.compression_utils import FileObjType
from galaxy.util.markdown import (
    indicate_data_truncated,
    literal_via_fence,
)
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.zipstream import ZipstreamWrapper
from . import (
    dataproviders as p_dataproviders,
    metadata,
)

if TYPE_CHECKING:
    from galaxy.datatypes.display_applications.application import DisplayApplication
    from galaxy.datatypes.registry import Registry

XSS_VULNERABLE_MIME_TYPES = [
    "image/svg+xml",  # Unfiltered by Galaxy and may contain JS that would be executed by some browsers.
    "application/xml",  # Some browsers will evaluate SVG embedded JS in such XML documents.
]
DEFAULT_MIME_TYPE = "text/plain"  # Vulnerable mime types will be replaced with this.

log = logging.getLogger(__name__)

# Valid first column and strand column values vor bed, other formats
col1_startswith = ["chr", "chl", "groupun", "reftig_", "scaffold", "super_", "vcho"]
valid_strand = ["+", "-", "."]

DOWNLOAD_FILENAME_PATTERN_DATASET = "Galaxy${hid}-[${name}].${ext}"
DOWNLOAD_FILENAME_PATTERN_COLLECTION_ELEMENT = "Galaxy${hdca_hid}-[${hdca_name}__${element_identifier}].${ext}"
DEFAULT_MAX_PEEK_SIZE = 1000000  # 1 MB

Headers = Dict[str, Any]


class DatatypeConverterNotFoundException(Exception):
    pass


class DatatypeValidation:
    def __init__(self, state: str, message: str) -> None:
        self.state = state
        self.message = message

    @staticmethod
    def validated() -> "DatatypeValidation":
        return DatatypeValidation("ok", "Dataset validated by datatype validator.")

    @staticmethod
    def invalid(message: str) -> "DatatypeValidation":
        return DatatypeValidation("invalid", message)

    @staticmethod
    def unvalidated() -> "DatatypeValidation":
        return DatatypeValidation(UNKNOWN, "Dataset validation unimplemented for this datatype.")

    def __repr__(self) -> str:
        return f"DatatypeValidation[state={self.state},message={self.message}]"


def validate(dataset_instance: DatasetProtocol) -> DatatypeValidation:
    try:
        datatype_validation = dataset_instance.datatype.validate(dataset_instance)
    except Exception as e:
        datatype_validation = DatatypeValidation.invalid(f"Problem running datatype validation method [{str(e)}]")
    return datatype_validation


def get_params_and_input_name(
    converter, deps: Optional[Dict], target_context: Optional[Dict] = None
) -> Tuple[Dict, str]:
    # Generate parameter dictionary
    params = {}
    # determine input parameter name and add to params
    input_name = "input1"
    for key, value in converter.inputs.items():
        if deps and value.name in deps:
            params[value.name] = deps[value.name]
        elif value.type == "data":
            input_name = key
        elif value.optional:
            params[value.name] = None

    # add potentially required/common internal tool parameters e.g. '__job_resource'
    if target_context:
        for key, value in target_context.items():
            if key.startswith("__"):
                params[key] = value
    return params, input_name


class DataMeta(type):
    """
    Metaclass for Data class.  Sets up metadata spec.
    """

    def __init__(cls, name, bases, dict_):
        cls.metadata_spec = metadata.MetadataSpecCollection()
        for base in bases:  # loop through bases (class/types) of cls
            if hasattr(base, "metadata_spec"):  # base of class Data (object) has no metadata
                cls.metadata_spec.update(base.metadata_spec)  # add contents of metadata spec of base class to cls
        metadata.Statement.process(cls)


def _is_binary_file(data):
    from galaxy.datatypes import binary

    return isinstance(data.datatype, binary.Binary) or type(data.datatype) is Data


def _get_max_peek_size(data):
    from galaxy.datatypes import (
        binary,
        text,
    )

    max_peek_size = DEFAULT_MAX_PEEK_SIZE  # 1 MB
    if isinstance(data.datatype, text.Html):
        max_peek_size = 10000000  # 10 MB for html
    elif isinstance(data.datatype, binary.Binary):
        max_peek_size = 100000  # 100 KB for binary
    return max_peek_size


def _get_file_size(data):
    file_size = int(data.dataset.file_size or 0)
    if file_size == 0:
        if data.dataset.object_store:
            file_size = data.dataset.object_store.size(data.dataset)
        else:
            file_size = os.stat(data.get_file_name()).st_size
    return file_size


@p_dataproviders.decorators.has_dataproviders
class Data(metaclass=DataMeta):
    """
    Base class for all datatypes.  Implements basic interfaces as well
    as class methods for metadata.

    >>> class DataTest( Data ):
    ...     MetadataElement( name="test" )
    ...
    >>> DataTest.metadata_spec.test.name
    'test'
    >>> DataTest.metadata_spec.test.desc
    'test'
    >>> type( DataTest.metadata_spec.test.param )
    <class 'galaxy.model.metadata.MetadataParameter'>
    """

    edam_data = "data_0006"
    edam_format = "format_1915"
    file_ext = "data"
    is_subclass = False
    # Data is not chunkable by default.
    CHUNKABLE = False

    #: Dictionary of metadata fields for this datatype
    metadata_spec: metadata.MetadataSpecCollection

    # Add metadata elements
    MetadataElement(
        name="dbkey",
        desc="Database/Build",
        default="?",
        param=metadata.DBKeyParameter,
        multiple=False,
        optional=True,
        no_value="?",
    )
    # Stores the set of display applications, and viewing methods, supported by this datatype
    supported_display_apps: Dict[str, Any] = {}
    # The dataset contains binary data --> do not space_to_tab or convert newlines, etc.
    # Allow binary file uploads of this type when True.
    is_binary: Union[bool, Literal["maybe"]] = True
    # Composite datatypes
    composite_type: Optional[str] = None
    composite_files: Dict[str, Any] = {}
    primary_file_name = "index"
    # Allow user to change between this datatype and others. If left to None,
    # datatype change is allowed if the datatype is not composite.
    allow_datatype_change: Optional[bool] = None
    # A per datatype setting (inherited): max file size (in bytes) for setting optional metadata
    _max_optional_metadata_filesize = None

    # Trackster track type.
    track_type: Optional[str] = None

    # Data sources.
    data_sources: Dict[str, str] = {}

    dataproviders: Dict[str, Any]

    def __init__(self, **kwd):
        """Initialize the datatype"""
        self.supported_display_apps = self.supported_display_apps.copy()
        self.composite_files = self.composite_files.copy()
        self.display_applications = {}

    @classmethod
    def is_datatype_change_allowed(cls) -> bool:
        """
        Returns the value of the `allow_datatype_change` class attribute if set
        in a subclass, or True iff the datatype is not composite.
        """
        if cls.allow_datatype_change is not None:
            return cls.allow_datatype_change
        return cls.composite_type is None

    def dataset_content_needs_grooming(self, file_name: str) -> bool:
        """This function is called on an output dataset file after the content is initially generated."""
        return False

    def groom_dataset_content(self, file_name: str) -> None:
        """This function is called on an output dataset file if dataset_content_needs_grooming returns True."""

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        # Metadata should be left mostly uninitialized.  Dataset will
        # handle returning default values when metadata is not set.
        # copy_from allows metadata to be passed in that will be
        # copied. (although this seems ambiguous, see
        # Dataset.set_metadata.  It always copies the rhs in order to
        # flag the object as modified for SQLAlchemy.
        if copy_from:
            dataset.metadata = copy_from.metadata

    def set_meta(self, dataset: DatasetProtocol, *, overwrite: bool = True, **kwd) -> None:
        """Unimplemented method, allows guessing of metadata from contents of file"""

    def missing_meta(self, dataset: HasMetadata, check: Optional[List] = None, skip: Optional[List] = None) -> bool:
        """
        Checks for empty metadata values.
        Returns False if no non-optional metadata is missing and the missing metadata key otherwise.
        Specifying a list of 'check' values will only check those names provided; when used, optionality is ignored
        Specifying a list of 'skip' items will return True even when a named metadata value is missing; when used, optionality is ignored
        """
        if skip is None:
            skip = []
        if check:
            to_check = check
        else:
            to_check = dataset.metadata.keys()
        for key in to_check:
            if key in skip:
                continue
            if not check and len(skip) == 0 and dataset.metadata.spec[key].get("optional"):
                continue  # we skip check for optional and nonrequested values here
            if not dataset.metadata.element_is_set(key) and (
                check or dataset.metadata.spec[key].check_required_metadata
            ):
                # FIXME: Optional metadata isn't always properly annotated,
                # so skip check if check_required_metadata is false on the datatype that defined the metadata element.
                # See https://github.com/galaxyproject/tools-iuc/issues/4367
                return key
        return False

    def set_max_optional_metadata_filesize(self, max_value: int) -> None:
        try:
            max_value = int(max_value)
        except (TypeError, ValueError):
            return
        self.__class__._max_optional_metadata_filesize = max_value

    def get_max_optional_metadata_filesize(self) -> int:
        rval = self.__class__._max_optional_metadata_filesize
        if rval is None:
            return -1
        return rval

    max_optional_metadata_filesize = property(get_max_optional_metadata_filesize, set_max_optional_metadata_filesize)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """
        Set the peek and blurb text
        """
        if not dataset.dataset.purged:
            dataset.peek = ""
            dataset.blurb = "data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML table, used for displaying peek"""
        if not dataset.peek:
            return "Peek not available"
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            data = dataset.peek
            lines = data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                out.append(f"<tr><td>{escape(unicodify(line, 'utf-8'))}</td></tr>")
            out.append("</table>")
            return "".join(out)
        except Exception as exc:
            return f"Can't create peek: {unicodify(exc)}"

    def _archive_main_file(
        self, archive: ZipstreamWrapper, display_name: str, data_filename: str
    ) -> Tuple[bool, str, str]:
        """Called from _archive_composite_dataset to add central file to archive.

        Unless subclassed, this will add the main dataset file (argument data_filename)
        to the archive, as an HTML file with its filename derived from the dataset name
        (argument outfname).

        Returns a tuple of boolean, string, string: (error, msg, messagetype)
        """
        error, msg, messagetype = False, "", ""
        archname = f"{display_name}.html"  # fake the real nature of the html file
        try:
            archive.write(data_filename, archname)
        except OSError:
            error = True
            log.exception("Unable to add composite parent %s to temporary library download archive", data_filename)
            msg = "Unable to create archive for download, please report this error"
            messagetype = "error"
        return error, msg, messagetype

    def _archive_composite_dataset(
        self, trans, data: DatasetHasHidProtocol, headers: Headers, do_action: str = "zip"
    ) -> Tuple[Union[ZipstreamWrapper, str], Headers]:
        # save a composite object into a compressed archive for downloading
        outfname = data.name[0:150]
        outfname = "".join(c in FILENAME_VALID_CHARS and c or "_" for c in outfname)
        archive = ZipstreamWrapper(
            archive_name=outfname,
            upstream_mod_zip=trans.app.config.upstream_mod_zip,
            upstream_gzip=trans.app.config.upstream_gzip,
        )
        error = False
        msg = ""
        ext = data.extension
        path = data.get_file_name()
        efp = data.extra_files_path
        # Add any central file to the archive,

        display_name = os.path.splitext(outfname)[0]
        if not display_name.endswith(ext):
            display_name = f"{display_name}_{ext}"

        error, msg = self._archive_main_file(archive, display_name, path)[:2]
        if not error:
            # Add any child files to the archive,
            for fpath, rpath in self.__archive_extra_files_path(extra_files_path=efp):
                try:
                    archive.write(fpath, rpath)
                except OSError:
                    error = True
                    log.exception("Unable to add %s to temporary library download archive", rpath)
                    msg = "Unable to create archive for download, please report this error"
                    continue
        if not error:
            headers.update(archive.get_headers())
            return archive, headers
        return trans.show_error_message(msg), headers

    def __archive_extra_files_path(self, extra_files_path: str) -> Generator[Tuple[str, str], None, None]:
        """Yield filepaths and relative filepaths for files in extra_files_path"""
        for root, _, files in os.walk(extra_files_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rpath = os.path.relpath(fpath, extra_files_path)
                yield fpath, rpath

    def _serve_raw(
        self, dataset: DatasetHasHidProtocol, to_ext: Optional[str], headers: Headers, **kwd
    ) -> Tuple[IO, Headers]:
        headers["Content-Length"] = str(os.stat(dataset.get_file_name()).st_size)
        headers["content-type"] = (
            "application/octet-stream"  # force octet-stream so Safari doesn't append mime extensions to filename
        )
        filename = self._download_filename(
            dataset,
            to_ext,
            hdca=kwd.get("hdca"),
            element_identifier=kwd.get("element_identifier"),
            filename_pattern=kwd.get("filename_pattern"),
        )
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return open(dataset.get_file_name(), mode="rb"), headers

    def to_archive(self, dataset: DatasetProtocol, name: str = "") -> Iterable:
        """
        Collect archive paths and file handles that need to be exported when archiving `dataset`.

        :param dataset: HistoryDatasetAssociation
        :param name: archive name, in collection context corresponds to collection name(s) and element_identifier,
                     joined by '/', e.g 'fastq_collection/sample1/forward'
        """
        rel_paths = []
        file_paths = []
        if dataset.datatype.composite_type or dataset.extension.endswith("html"):
            main_file = f"{name}.html"
            rel_paths.append(main_file)
            file_paths.append(dataset.get_file_name())
            for fpath, rpath in self.__archive_extra_files_path(dataset.extra_files_path):
                rel_paths.append(os.path.join(name, rpath))
                file_paths.append(fpath)
        else:
            rel_paths.append(f"{name or dataset.get_file_name()}.{dataset.extension}")
            file_paths.append(dataset.get_file_name())
        return zip(file_paths, rel_paths)

    def _serve_file_download(self, headers, data, trans, to_ext, file_size, **kwd):
        composite_extensions = trans.app.datatypes_registry.get_composite_extensions()
        composite_extensions.append("html")  # for archiving composite datatypes
        composite_extensions.append("data_manager_json")  # for downloading bundles if bundled.

        if data.extension in composite_extensions:
            return self._archive_composite_dataset(trans, data, headers, do_action=kwd.get("do_action", "zip"))
        else:
            headers["Content-Length"] = str(file_size)
            filename = self._download_filename(
                data,
                to_ext,
                hdca=kwd.get("hdca"),
                element_identifier=kwd.get("element_identifier"),
                filename_pattern=kwd.get("filename_pattern"),
            )
            headers["content-type"] = (
                "application/octet-stream"  # force octet-stream so Safari doesn't append mime extensions to filename
            )
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            return open(data.get_file_name(), "rb"), headers

    def _serve_binary_file_contents_as_text(self, trans, data, headers, file_size, max_peek_size):
        headers["content-type"] = "text/html"
        with open(data.get_file_name(), "rb") as fh:
            return (
                trans.fill_template_mako(
                    "/dataset/binary_file.mako",
                    data=data,
                    file_contents=fh.read(max_peek_size),
                    file_size=util.nice_size(file_size),
                    truncated=file_size > max_peek_size,
                ),
                headers,
            )

    def _serve_file_contents(self, trans, data, headers, preview, file_size, max_peek_size):
        from galaxy.datatypes import images

        preview = util.string_as_bool(preview)
        if not preview or isinstance(data.datatype, images.Image) or file_size < max_peek_size:
            return self._yield_user_file_content(trans, data, data.get_file_name(), headers), headers

        with compression_utils.get_fileobj(data.get_file_name(), "rb") as fh:
            # preview large text file
            headers["content-type"] = "text/html"
            return (
                trans.fill_template_mako(
                    "/dataset/large_file.mako",
                    truncated_data=fh.read(max_peek_size),
                    data=data,
                ),
                headers,
            )

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd,
    ):
        """
        Displays data in central pane if preview is `True`, else handles download.

        Datatypes should be very careful if overriding this method and this interface
        between datatypes and Galaxy will likely change.

        TODO: Document alternatives to overriding this method (data
        providers?).
        """
        headers = kwd.get("headers", {})
        # Prevent IE8 from sniffing content type since we're explicit about it.  This prevents intentionally text/plain
        # content from being rendered in the browser
        headers["X-Content-Type-Options"] = "nosniff"

        if filename and filename != "index":
            # For files in extra_files_path
            extra_dir = dataset.dataset.extra_files_path_name
            file_path = trans.app.object_store.get_filename(dataset.dataset, extra_dir=extra_dir, alt_name=filename)
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    with tempfile.NamedTemporaryFile(
                        mode="w", delete=False, dir=trans.app.config.new_file_path, prefix="gx_html_autocreate_"
                    ) as tmp_fh:
                        tmp_file_name = tmp_fh.name
                        dir_items = sorted(os.listdir(file_path))
                        base_path, item_name = os.path.split(file_path)
                        tmp_fh.write(
                            "<html><head><h3>Directory %s contents: %d items</h3></head>\n"
                            % (escape(item_name), len(dir_items))
                        )
                        tmp_fh.write('<body><p/><table cellpadding="2">\n')
                        for index, fname in enumerate(dir_items):
                            if index % 2 == 0:
                                bgcolor = "#D8D8D8"
                            else:
                                bgcolor = "#FFFFFF"
                            # Can't have an href link here because there is no route
                            # defined for files contained within multiple subdirectory
                            # levels of the primary dataset.  Something like this is
                            # close, but not quite correct:
                            # href = url_for(controller='dataset', action='display',
                            # dataset_id=trans.security.encode_id(dataset.dataset.id),
                            # preview=preview, filename=fname, to_ext=to_ext)
                            tmp_fh.write(f'<tr bgcolor="{bgcolor}"><td>{escape(fname)}</td></tr>\n')
                        tmp_fh.write("</table></body></html>\n")
                    return self._yield_user_file_content(trans, dataset, tmp_file_name, headers), headers
                mime = mimetypes.guess_type(file_path)[0]
                if not mime:
                    try:
                        mime = trans.app.datatypes_registry.get_mimetype_by_extension(file_path.split(".")[-1])
                    except Exception:
                        mime = "text/plain"
                self._clean_and_set_mime_type(trans, mime, headers)  # type: ignore[arg-type]
                return self._yield_user_file_content(trans, dataset, file_path, headers), headers
            else:
                raise ObjectNotFound(f"Could not find '{filename}' on the extra files path {file_path}.")
        self._clean_and_set_mime_type(trans, dataset.get_mime(), headers)

        downloading = to_ext is not None
        file_size = _get_file_size(dataset)

        if not os.path.exists(dataset.get_file_name()):
            raise ObjectNotFound(f"File Not Found ({dataset.get_file_name()}).")

        if downloading:
            trans.log_event(f"Download dataset id: {str(dataset.id)}")
            return self._serve_file_download(headers, dataset, trans, to_ext, file_size, **kwd)
        else:  # displaying
            trans.log_event(f"Display dataset id: {str(dataset.id)}")
            max_peek_size = _get_max_peek_size(dataset)
            if (
                _is_binary_file(dataset) and preview and hasattr(trans, "fill_template_mako")
            ):  # preview file which format is unknown (to Galaxy), we still try to display this as text
                return self._serve_binary_file_contents_as_text(trans, dataset, headers, file_size, max_peek_size)
            else:  # text/html, or image, or display was called without preview flag
                return self._serve_file_contents(trans, dataset, headers, preview, file_size, max_peek_size)

    def display_as_markdown(self, dataset_instance: DatasetProtocol) -> str:
        """Prepare for embedding dataset into a basic Markdown document.

        This is a somewhat experimental interface and should not be implemented
        on datatypes not tightly tied to a Galaxy version (e.g. datatypes in the
        Tool Shed).

        Speaking very loosely - the datatype should load a bounded amount
        of data from the supplied dataset instance and prepare for embedding it
        into Markdown. This should be relatively vanilla Markdown - the result of
        this is bleached and it should not contain nested Galaxy Markdown
        directives.

        If the data cannot reasonably be displayed, just indicate this and do
        not throw an exception.
        """
        if self.file_ext in {"png", "jpg"}:
            return self.handle_dataset_as_image(dataset_instance)
        if self.is_binary:
            result = "*cannot display binary content*\n"
        else:
            with open(dataset_instance.get_file_name()) as f:
                contents = f.read(DEFAULT_MAX_PEEK_SIZE)
            result = literal_via_fence(contents)
            if len(contents) == DEFAULT_MAX_PEEK_SIZE:
                result += indicate_data_truncated()
        return result

    def _yield_user_file_content(self, trans, from_dataset: HasCreatingJob, filename: str, headers: Headers) -> IO:
        """This method is responsible for sanitizing the HTML if needed."""
        if trans.app.config.sanitize_all_html and headers.get("content-type", None) == "text/html":
            # Sanitize anytime we respond with plain text/html content.
            # Check to see if this dataset's parent job is allowlisted
            # We cannot currently trust imported datasets for rendering.
            if not from_dataset.creating_job.imported and from_dataset.creating_job.tool_id.startswith(
                tuple(trans.app.config.sanitize_allowlist)
            ):
                return open(filename, mode="rb")

            # This is returning to the browser, it needs to be encoded.
            # TODO Ideally this happens a layer higher, but this is a bad
            # issue affecting many tools
            with open(filename) as f:
                return sanitize_html(f.read()).encode("utf-8")

        return open(filename, mode="rb")

    def _download_filename(
        self,
        dataset: DatasetHasHidProtocol,
        to_ext: Optional[str] = None,
        hdca: Optional[DatasetHasHidProtocol] = None,
        element_identifier: Optional[str] = None,
        filename_pattern: Optional[str] = None,
    ) -> str:
        def escape(raw_identifier):
            return "".join(c in FILENAME_VALID_CHARS and c or "_" for c in raw_identifier)[0:150]

        if not to_ext or to_ext == "data":
            # If a client requests to_ext with the extension 'data', they are
            # deferring to the server, set it based on datatype.
            to_ext = dataset.extension

        template_values = {
            "name": escape(dataset.name),
            "ext": to_ext,
            "hid": dataset.hid,
        }

        if not filename_pattern:
            if hdca is None:
                filename_pattern = DOWNLOAD_FILENAME_PATTERN_DATASET
            else:
                filename_pattern = DOWNLOAD_FILENAME_PATTERN_COLLECTION_ELEMENT

        if hdca is not None:
            # Use collection context to build up filename.
            template_values["element_identifier"] = element_identifier
            template_values["hdca_name"] = escape(hdca.name)
            template_values["hdca_hid"] = hdca.hid

        return string.Template(filename_pattern).substitute(**template_values)

    def display_name(self, dataset: HasName) -> str:
        """Returns formatted html of dataset name"""
        try:
            return escape(unicodify(dataset.name, "utf-8"))
        except Exception:
            return "name unavailable"

    def display_info(self, dataset: HasInfo) -> str:
        """Returns formatted html of dataset info"""
        try:
            # Change new line chars to html
            info: str = escape(dataset.info)
            if info.find("\r\n") >= 0:
                info = info.replace("\r\n", "<br/>")
            if info.find("\r") >= 0:
                info = info.replace("\r", "<br/>")
            if info.find("\n") >= 0:
                info = info.replace("\n", "<br/>")

            info = unicodify(info, "utf-8")

            return info
        except Exception:
            return "info unavailable"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "application/octet-stream"

    def add_display_app(self, app_id: str, label: str, file_function: str, links_function: str) -> None:
        """
        Adds a display app to the datatype.
        app_id is a unique id
        label is the primary display label, e.g., display at 'UCSC'
        file_function is a string containing the name of the function that returns a properly formatted display
        links_function is a string containing the name of the function that returns a list of (link_name,link)
        """
        self.supported_display_apps = self.supported_display_apps.copy()
        self.supported_display_apps[app_id] = {
            "label": label,
            "file_function": file_function,
            "links_function": links_function,
        }

    def remove_display_app(self, app_id: str) -> None:
        """Removes a display app from the datatype"""
        self.supported_display_apps = self.supported_display_apps.copy()
        try:
            del self.supported_display_apps[app_id]
        except Exception:
            log.exception(
                "Tried to remove display app %s from datatype %s, but this display app is not declared.",
                type,
                self.__class__.__name__,
            )

    def clear_display_apps(self) -> None:
        self.supported_display_apps = {}

    def add_display_application(self, display_application: "DisplayApplication") -> None:
        """New style display applications"""
        assert display_application.id not in self.display_applications, "Attempted to add a display application twice"
        self.display_applications[display_application.id] = display_application

    def get_display_application(self, key: str, default: Optional["DisplayApplication"] = None) -> "DisplayApplication":
        return self.display_applications.get(key, default)

    def get_display_applications_by_dataset(self, dataset: DatasetProtocol, trans) -> Dict[str, "DisplayApplication"]:
        rval = {}
        for key, value in self.display_applications.items():
            value = value.filter_by_dataset(dataset, trans)
            if value.links:
                rval[key] = value
        return rval

    def get_display_types(self) -> List[str]:
        """Returns display types available"""
        return list(self.supported_display_apps.keys())

    def get_display_label(self, type: str) -> str:
        """Returns primary label for display app"""
        try:
            return self.supported_display_apps[type]["label"]
        except Exception:
            return UNKNOWN

    def as_display_type(self, dataset: DatasetProtocol, type: str, **kwd) -> Union[FileObjType, str]:
        """Returns modified file contents for a particular display type"""
        try:
            if type in self.get_display_types():
                return getattr(self, self.supported_display_apps[type]["file_function"])(dataset, **kwd)
        except Exception:
            log.exception(
                "Function %s is referred to in datatype %s for displaying as type %s, but is not accessible",
                self.supported_display_apps[type]["file_function"],
                self.__class__.__name__,
                type,
            )
        return f"This display type ({type}) is not implemented for this datatype ({dataset.ext})."

    def get_display_links(
        self, dataset: DatasetProtocol, type: str, app, base_url: str, target_frame: str = "_blank", **kwd
    ):
        """
        Returns a list of tuples of (name, link) for a particular display type.  No check on
        'access' permissions is done here - if you can view the dataset, you can also save it
        or send it to a destination outside of Galaxy, so Galaxy security restrictions do not
        apply anyway.
        """
        try:
            if app.config.enable_old_display_applications and type in self.get_display_types():
                return target_frame, getattr(self, self.supported_display_apps[type]["links_function"])(
                    dataset, type, app, base_url, **kwd
                )
        except Exception:
            log.exception(
                "Function %s is referred to in datatype %s for generating links for type %s, but is not accessible",
                self.supported_display_apps[type]["links_function"],
                self.__class__.__name__,
                type,
            )
        return target_frame, []

    def get_converter_types(self, original_dataset: HasExt, datatypes_registry: "Registry") -> Dict[str, Dict]:
        """Returns available converters by type for this dataset"""
        return datatypes_registry.get_converters_by_datatype(original_dataset.ext)

    def find_conversion_destination(
        self, dataset: DatasetProtocol, accepted_formats: List[str], datatypes_registry, **kwd
    ) -> Tuple[bool, Optional[str], Any]:
        """Returns ( direct_match, converted_ext, existing converted dataset )"""
        return datatypes_registry.find_conversion_destination_for_dataset_by_extensions(
            dataset, accepted_formats, **kwd
        )

    def convert_dataset(
        self,
        trans,
        original_dataset: DatasetHasHidProtocol,
        target_type: str,
        return_output: bool = False,
        visible: bool = True,
        deps: Optional[Dict] = None,
        target_context: Optional[Dict] = None,
        history=None,
    ):
        """This function adds a job to the queue to convert a dataset to another type. Returns a message about success/failure."""
        converter = trans.app.datatypes_registry.get_converter_by_target_type(original_dataset.ext, target_type)

        if converter is None:
            raise DatatypeConverterNotFoundException(
                f"A converter does not exist for {original_dataset.ext} to {target_type}."
            )

        params, input_name = get_params_and_input_name(converter, deps, target_context)

        params[input_name] = original_dataset
        # Make the target datatype available to the converter
        params["__target_datatype__"] = target_type
        # Run converter, job is dispatched through Queue
        job, converted_datasets, *_ = converter.execute(
            trans, incoming=params, set_output_hid=visible, history=history, flush_job=False
        )
        for converted_dataset in converted_datasets.values():
            original_dataset.attach_implicitly_converted_dataset(trans.sa_session, converted_dataset, target_type)
        trans.app.job_manager.enqueue(job, tool=converter)
        if len(params) > 0:
            trans.log_event(f"Converter params: {str(params)}", tool_id=converter.id)
        if not visible:
            for value in converted_datasets.values():
                value.visible = False
        if return_output:
            return converted_datasets
        return f"The file conversion of {converter.name} on data {original_dataset.hid} has been added to the Queue."

    # We need to clear associated files before we set metadata
    # so that as soon as metadata starts to be set, e.g. implicitly converted datasets are deleted and no longer available 'while' metadata is being set, not just after
    # We'll also clear after setting metadata, for backwards compatibility
    def after_setting_metadata(self, dataset: HasClearAssociatedFiles) -> None:
        """This function is called on the dataset after metadata is set."""
        dataset.clear_associated_files(metadata_safe=True)

    def before_setting_metadata(self, dataset: HasClearAssociatedFiles) -> None:
        """This function is called on the dataset before metadata is set."""
        dataset.clear_associated_files(metadata_safe=True)

    def __new_composite_file(
        self,
        name: str,
        optional: bool = False,
        mimetype: Optional[str] = None,
        description: Optional[str] = None,
        substitute_name_with_metadata: Optional[str] = None,
        is_binary: bool = False,
        to_posix_lines: bool = True,
        space_to_tab: bool = False,
        **kwds,
    ) -> Bunch:
        kwds["name"] = name
        kwds["optional"] = optional
        kwds["mimetype"] = mimetype
        kwds["description"] = description
        kwds["substitute_name_with_metadata"] = substitute_name_with_metadata
        kwds["is_binary"] = is_binary
        kwds["to_posix_lines"] = to_posix_lines
        kwds["space_to_tab"] = space_to_tab

        composite_file = Bunch(**kwds)
        return composite_file

    def add_composite_file(self, name: str, **kwds) -> None:
        # self.composite_files = self.composite_files.copy()
        self.composite_files[name] = self.__new_composite_file(name, **kwds)

    @property
    def writable_files(self):
        files = {}
        if self.composite_type != "auto_primary_file":
            files[self.primary_file_name] = self.__new_composite_file(self.primary_file_name)
        for key, value in self.get_composite_files().items():
            files[key] = value
        return files

    def get_writable_files_for_dataset(self, dataset: Optional[HasMetadata]) -> Dict:
        files = {}
        if self.composite_type != "auto_primary_file":
            files[self.primary_file_name] = self.__new_composite_file(self.primary_file_name)
        for key, value in self.get_composite_files(dataset).items():
            files[key] = value
        return files

    def get_composite_files(self, dataset: Optional[HasMetadata] = None):
        def substitute_composite_key(key, composite_file):
            if composite_file.substitute_name_with_metadata:
                if dataset:
                    meta_value = str(dataset.metadata.get(composite_file.substitute_name_with_metadata))
                else:
                    meta_value = self.metadata_spec[composite_file.substitute_name_with_metadata].default
                return key % meta_value
            return key

        files = {}
        for key, value in self.composite_files.items():
            files[substitute_composite_key(key, value)] = value
        return files

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        raise Exception("generate_primary_file is not implemented for this datatype.")

    @property
    def has_resolution(self):
        return False

    def matches_any(self, target_datatypes: List[Any]) -> bool:
        """
        Check if this datatype is of any of the target_datatypes or is
        a subtype thereof.
        """
        datatype_classes = tuple(datatype if isclass(datatype) else datatype.__class__ for datatype in target_datatypes)
        return isinstance(self, datatype_classes)

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """
        Merge files with copy.copyfileobj() will not hit the
        max argument limitation of cat. gz and bz2 files are also working.
        """
        if not split_files:
            raise ValueError(f"Asked to merge zero files as {output_file}")
        elif len(split_files) == 1:
            shutil.copyfileobj(open(split_files[0], "rb"), open(output_file, "wb"))
        else:
            with open(output_file, "wb") as fdst:
                for fsrc in split_files:
                    shutil.copyfileobj(open(fsrc, "rb"), fdst)

    # ------------- Dataproviders
    def has_dataprovider(self, data_format: str) -> bool:
        """
        Returns True if `data_format` is available in `dataproviders`.
        """
        return data_format in self.dataproviders

    def dataprovider(self, dataset: DatasetProtocol, data_format: str, **settings):
        """
        Base dataprovider factory for all datatypes that returns the proper provider
        for the given `data_format` or raises a `NoProviderAvailable`.
        """
        if self.has_dataprovider(data_format):
            return self.dataproviders[data_format](self, dataset, **settings)
        raise p_dataproviders.exceptions.NoProviderAvailable(self, data_format)

    def validate(self, dataset: DatasetProtocol, **kwd) -> DatatypeValidation:
        return DatatypeValidation.unvalidated()

    @p_dataproviders.decorators.dataprovider_factory("base")
    def base_dataprovider(self, dataset: DatasetProtocol, **settings) -> p_dataproviders.base.DataProvider:
        dataset_source = p_dataproviders.dataset.DatasetDataProvider(dataset)
        return p_dataproviders.base.DataProvider(dataset_source, **settings)

    @p_dataproviders.decorators.dataprovider_factory("chunk", p_dataproviders.chunk.ChunkDataProvider.settings)
    def chunk_dataprovider(self, dataset: DatasetProtocol, **settings) -> p_dataproviders.chunk.ChunkDataProvider:
        dataset_source = p_dataproviders.dataset.DatasetDataProvider(dataset)
        return p_dataproviders.chunk.ChunkDataProvider(dataset_source, **settings)

    @p_dataproviders.decorators.dataprovider_factory("chunk64", p_dataproviders.chunk.Base64ChunkDataProvider.settings)
    def chunk64_dataprovider(
        self, dataset: DatasetProtocol, **settings
    ) -> p_dataproviders.chunk.Base64ChunkDataProvider:
        dataset_source = p_dataproviders.dataset.DatasetDataProvider(dataset)
        return p_dataproviders.chunk.Base64ChunkDataProvider(dataset_source, **settings)

    def _clean_and_set_mime_type(self, trans, mime: str, headers: Headers) -> None:
        if mime.lower() in XSS_VULNERABLE_MIME_TYPES:
            if not getattr(trans.app.config, "serve_xss_vulnerable_mimetypes", True):
                mime = DEFAULT_MIME_TYPE
        headers["content-type"] = mime

    def handle_dataset_as_image(self, hda: DatasetProtocol) -> str:
        raise Exception("Unimplemented Method")

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state.pop("display_applications", None)
        return state


@p_dataproviders.decorators.has_dataproviders
class Text(Data):
    edam_format = "format_2330"
    file_ext = "txt"
    line_class = "line"

    is_binary = False

    # Add metadata elements
    MetadataElement(
        name="data_lines",
        default=0,
        desc="Number of data lines",
        readonly=True,
        optional=True,
        visible=False,
        no_value=0,
    )

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "text/plain"

    def set_meta(self, dataset: DatasetProtocol, *, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.data_lines = self.count_data_lines(dataset)

    def estimate_file_lines(self, dataset: DatasetProtocol) -> Optional[int]:
        """
        Perform a rough estimate by extrapolating number of lines from a small read.
        """
        sample_size = 1048576
        try:
            with compression_utils.get_fileobj(dataset.get_file_name()) as dataset_fh:
                dataset_read = dataset_fh.read(sample_size)
            sample_lines = dataset_read.count("\n")
            return int(sample_lines * (float(dataset.get_size()) / float(sample_size)))
        except UnicodeDecodeError:
            log.warning(f"Unable to estimate lines in file {dataset.get_file_name()}, likely not a text file.")
            return None

    def count_data_lines(self, dataset: HasFileName) -> Optional[int]:
        """
        Count the number of lines of data in dataset,
        skipping all blank lines and comments.
        """
        CHUNK_SIZE = 2**15  # 32Kb
        data_lines = 0
        with compression_utils.get_fileobj(dataset.get_file_name()) as in_file:
            # FIXME: Potential encoding issue can prevent the ability to iterate over lines
            # causing set_meta process to fail otherwise OK jobs. A better solution than
            # a silent try/except is desirable.
            try:
                for line in iter_start_of_line(in_file, CHUNK_SIZE):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        data_lines += 1
            except UnicodeDecodeError:
                log.warning(f"Unable to count lines in file {dataset.get_file_name()}, likely not a text file.")
                return None
        return data_lines

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """
        Set the peek.  This method is used by various subclasses of Text.
        """
        line_count = kwd.get("line_count")
        width = kwd.get("width", 256)
        skipchars = kwd.get("skipchars")
        line_wrap = kwd.get("line_wrap", True)

        if not dataset.dataset.purged:
            # The file must exist on disk for the get_file_peek() method
            dataset.peek = get_file_peek(dataset.get_file_name(), width=width, skipchars=skipchars, line_wrap=line_wrap)
            if line_count is None:
                # See if line_count is stored in the metadata
                if dataset.metadata.data_lines:
                    dataset.blurb = f"{util.commaify(str(dataset.metadata.data_lines))} {inflector.cond_plural(dataset.metadata.data_lines, self.line_class)}"
                else:
                    # Number of lines is not known ( this should not happen ), and auto-detect is
                    # needed to set metadata
                    # This can happen when the file is larger than max_optional_metadata_filesize.
                    if int(dataset.get_size()) <= 1048576:
                        # Small dataset, recount all lines and reset peek afterward.
                        lc = self.count_data_lines(dataset)
                        if lc is not None:
                            dataset.metadata.data_lines = lc
                            dataset.blurb = f"{util.commaify(str(lc))} {inflector.cond_plural(lc, self.line_class)}"
                        else:
                            dataset.blurb = "Error: Cannot count lines in dataset"
                    else:
                        est_lines = self.estimate_file_lines(dataset)
                        if est_lines is not None:
                            dataset.blurb = f"~{util.shorten_with_metric_prefix(est_lines)} {inflector.cond_plural(est_lines, self.line_class)}"
                        else:
                            dataset.blurb = "Error: Cannot estimate lines in dataset"
            else:
                dataset.blurb = f"{util.commaify(str(line_count))} {inflector.cond_plural(line_count, self.line_class)}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """
        Split the input files by line.
        """
        if split_params is None:
            return

        if len(input_datasets) > 1:
            raise Exception("Text file splitting does not support multiple files")
        input_files = [ds.get_file_name() for ds in input_datasets]

        lines_per_file = None
        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            lines_per_file = []

            # Computing the length is expensive!
            def _file_len(fname):
                with open(fname) as f:
                    return sum(1 for _ in f)

            length = _file_len(input_files[0])
            parts = int(split_params["split_size"])
            if length < parts:
                parts = length
            len_each, remainder = divmod(length, parts)
            while length > 0:
                chunk = len_each
                if remainder > 0:
                    chunk += 1
                lines_per_file.append(chunk)
                remainder -= 1
                length -= chunk
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        f = open(input_files[0])
        try:
            chunk_idx = 0
            file_done = False
            part_file = None
            while not file_done:
                if lines_per_file is None:
                    this_chunk_size = chunk_size
                elif chunk_idx < len(lines_per_file):
                    this_chunk_size = lines_per_file[chunk_idx]
                    chunk_idx += 1
                lines_remaining = this_chunk_size
                part_file = None
                while lines_remaining > 0:
                    a_line = f.readline()
                    if a_line == "":
                        file_done = True
                        break
                    if part_file is None:
                        part_dir = subdir_generator_function()
                        part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
                        part_file = open(part_path, "w")
                    part_file.write(a_line)
                    lines_remaining -= 1
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise
        finally:
            f.close()
            if part_file:
                part_file.close()

    # ------------- Dataproviders
    @p_dataproviders.decorators.dataprovider_factory("line", p_dataproviders.line.FilteredLineDataProvider.settings)
    def line_dataprovider(self, dataset: DatasetProtocol, **settings) -> p_dataproviders.line.FilteredLineDataProvider:
        """
        Returns an iterator over the dataset's lines (that have been stripped)
        optionally excluding blank lines and lines that start with a comment character.
        """
        dataset_source = p_dataproviders.dataset.DatasetDataProvider(dataset)
        return p_dataproviders.line.FilteredLineDataProvider(dataset_source, **settings)

    @p_dataproviders.decorators.dataprovider_factory("regex-line", p_dataproviders.line.RegexLineDataProvider.settings)
    def regex_line_dataprovider(
        self, dataset: DatasetProtocol, **settings
    ) -> p_dataproviders.line.RegexLineDataProvider:
        """
        Returns an iterator over the dataset's lines
        optionally including/excluding lines that match one or more regex filters.
        """
        dataset_source = p_dataproviders.dataset.DatasetDataProvider(dataset)
        return p_dataproviders.line.RegexLineDataProvider(dataset_source, **settings)


class Directory(Data):
    """Class representing a directory of files."""

    file_ext = "directory"

    # The behavior of this class is intended to be similar to that of
    # composite types, but with arbitrary structure of extra_files.

    # A prioritized list of files in the directory that, if present, can serve
    # as a replacement for a composite type's primary dataset.
    recognized_index_files: List[str] = []

    # Directories converted from archives, and possibly others, have a single
    # root folder inside the directory. The root_folder attribute lets tools
    # access that folder without first exploring the directory tree themselves.
    # Will be set to the empty string for flat directories.
    MetadataElement(
        name="root_folder",
        default=None,
        desc="Name of the root folder of the directory",
        readonly=True,
        optional=False,
        visible=False,
    )

    # Capture the actual index file obtained from the recognized_index_files
    # list for a concrete directory.
    MetadataElement(
        name="index_file",
        default=None,
        desc="Name of the index file relative to the root folder",
        readonly=True,
        optional=False,
        visible=False,
    )

    def set_meta(self, dataset: DatasetProtocol, **kwd):
        efp = dataset.extra_files_path
        efp_items = os.listdir(efp)
        root_folder_name = efp_items[0]
        if len(efp_items) == 1 and os.path.isdir(os.path.join(efp, root_folder_name)):
            dataset.metadata.root_folder = root_folder_name
        else:
            dataset.metadata.root_folder = ""
        index_file = None
        for f in self.recognized_index_files:
            if os.path.isfile(os.path.join(efp, root_folder_name, f)):
                index_file = f
                break
        dataset.metadata.index_file = index_file

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = f"{dataset.metadata.root_folder}"
            dataset.blurb = nice_size(dataset.dataset.total_size)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def _archive_main_file(
        self, archive: ZipstreamWrapper, display_name: str, data_filename: str
    ) -> Tuple[bool, str, str]:
        """Overwrites the method to not do anything.

        No main file gets added to a directory archive.
        """
        error, msg, messagetype = False, "", ""
        return error, msg, messagetype

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd,
    ):
        headers = kwd.get("headers", {})
        # Prevent IE8 from sniffing content type since we're explicit about it.  This prevents intentionally text/plain
        # content from being rendered in the browser
        headers["X-Content-Type-Options"] = "nosniff"
        if to_ext:
            # Download the directory structure as an archive
            trans.log_event(f"Download directory for dataset id: {str(dataset.id)}")
            return self._archive_composite_dataset(trans, dataset, headers, do_action=kwd.get("do_action", "zip"))
        if preview:
            root_folder = dataset.metadata.root_folder
            index_file = dataset.metadata.index_file
            if not filename or filename == 'index':
                if root_folder is not None and index_file:
                    # display the index file in lieu of the empty primary dataset
                    file_path = os.path.join(dataset.extra_files_path, root_folder, index_file)
                    self._clean_and_set_mime_type(trans, "text/plain", headers)  # type: ignore[arg-type]
                    return self._yield_user_file_content(
                        trans,
                        dataset,
                        file_path,
                        headers
                    ), headers
                elif root_folder:
                    # delegate to the parent method, which knows how to display
                    # a directory
                    filename = root_folder
                else:
                    # No meaningful display available, show an info message instead
                    self._clean_and_set_mime_type(trans, "text/plain", headers)  # type: ignore[arg-type]
                    if root_folder is None:
                        return util.smart_str("Cannot generate preview with incomplete metadata. Resetting metadata may help.")
                    elif self.recognized_index_files:
                        return util.smart_str("None of the known key files for the datatype present. Is the datatype format set correctly?")
                    else:
                        return util.smart_str("No preview available for this dataset."), headers

        return super().display_data(
            trans,
            dataset=dataset,
            filename=filename,
            **kwd,
        )


class GenericAsn1(Text):
    """Class for generic ASN.1 text format"""

    edam_data = "data_0849"
    edam_format = "format_1966"
    file_ext = "asn1"


class LineCount(Text):
    """
    Dataset contains a single line with a single integer that denotes the
    line count for a related dataset. Used for custom builds.
    """


class Newick(Text):
    """New Hampshire/Newick Format"""

    edam_data = "data_0872"
    edam_format = "format_1910"
    file_ext = "newick"

    def sniff(self, filename: str) -> bool:
        """Returning false as the newick format is too general and cannot be sniffed."""
        return False


@build_sniff_from_prefix
class Nexus(Text):
    """Nexus format as used By Paup, Mr Bayes, etc"""

    edam_data = "data_0872"
    edam_format = "format_1912"
    file_ext = "nex"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """All Nexus Files Simply puts a '#NEXUS' in its first line"""
        return file_prefix.string_io().read(6).upper() == "#NEXUS"


# ------------- Utility methods --------------

# nice_size used to be here, but to resolve cyclical dependencies it's been
# moved to galaxy.util.  It belongs there anyway since it's used outside
# datatypes.
nice_size = util.nice_size


def get_test_fname(fname):
    """Returns test data filename"""
    path = os.path.dirname(__file__)
    full_path = os.path.join(path, "test", fname)
    return full_path


def get_file_peek(file_name, width=256, line_count=5, skipchars=None, line_wrap=True):
    """
    Returns the first line_count lines wrapped to width.

    >>> def assert_peek_is(file_name, expected, *args, **kwd):
    ...     path = get_test_fname(file_name)
    ...     peek = get_file_peek(path, *args, **kwd)
    ...     assert peek == expected, "%s != %s" % (peek, expected)
    >>> assert_peek_is('0_nonewline', u'0')
    >>> assert_peek_is('0.txt', u'0\\n')
    >>> assert_peek_is('4.bed', u'chr22\\t30128507\\t31828507\\tuc003bnx.1_cds_2_0_chr22_29227_f\\t0\\t+\\n', line_count=1)
    >>> assert_peek_is('1.bed', u'chr1\\t147962192\\t147962580\\tCCDS989.1_cds_0_0_chr1_147962193_r\\t0\\t-\\nchr1\\t147984545\\t147984630\\tCCDS990.1_cds_0_0_chr1_147984546_f\\t0\\t+\\n', line_count=2)
    """
    # Set size for file.readline() to a negative number to force it to
    # read until either a newline or EOF.  Needed for datasets with very
    # long lines.
    if width == "unlimited":
        width = -1
    if skipchars is None:
        skipchars = []
    lines = []
    count = 0

    last_line_break = False
    with compression_utils.get_fileobj(file_name) as temp:
        while count < line_count:
            try:
                line = temp.readline(width)
            except UnicodeDecodeError:
                return "binary file"
            if line == "":
                break
            last_line_break = False
            if line.endswith("\n"):
                line = line[:-1]
                last_line_break = True
            elif not line_wrap:
                for i in file_reader(temp, 1):
                    if i == "\n":
                        last_line_break = True
                    if not i or i == "\n":
                        break
            skip_line = False
            for skipchar in skipchars:
                if line.startswith(skipchar):
                    skip_line = True
                    break
            if not skip_line:
                lines.append(line)
                count += 1
    return "\n".join(lines) + ("\n" if last_line_break else "")
