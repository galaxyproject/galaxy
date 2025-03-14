import logging
import zlib
from dataclasses import (
    dataclass,
    fields,
)
from struct import unpack
from typing import (
    Dict,
    Optional,
)
from urllib.parse import (
    parse_qs,
    unquote,
    urlparse,
)

import requests
from typing_extensions import Unpack

from galaxy.files import OptionalUserContext
from . import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    PluginKind,
)

log = logging.getLogger(__name__)


@dataclass
class FileExtractParameters:
    source: str
    header_offset: int
    compression_method: int
    compress_size: int


DOC_TEMPLATE = """
Remote ZIP archive extractor
---------------------------

This plugin extracts files from a public remotely hosted ZIP archive using byte-range requests.
The following parameters are required and assumed to be known in advance:

- `source`: The URL of the remote ZIP archive.
- `header_offset`: The offset of the file header in the archive.
- `compression_method`: The compression method used for the file.
- `compress_size`: The size of the compressed file.
"""


class RemoteZipFilesSource(BaseFilesSource):
    plugin_type = "remoteZip"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        kwds: FilesSourceProperties = {
            "id": "extract",
            "label": "Remote ZIP extractor",
            "doc": DOC_TEMPLATE,
            "writable": False,
            "browsable": False,
        }
        kwds.update(kwd)
        props = self._parse_common_config_opts(kwds)
        self._props = props

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        params = extract_query_parameters(source_path)
        file_extract_params = validate_params(params)
        stream_and_decompress(file_extract_params, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("zip://"):
            return len("zip://")
        else:
            return 0

    def _serialization_props(self, user_context: OptionalUserContext = None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props


def extract_query_parameters(url: str) -> Dict[str, str]:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return {key: value[0] for key, value in query_params.items()}


def validate_params(params: Dict[str, str]) -> FileExtractParameters:
    """Validates and converts the params dictionary to a FileExtractParameters instance."""

    required_fields = [field.name for field in fields(FileExtractParameters)]

    # Ensure all required fields are present
    for field in required_fields:
        if field not in params:
            raise ValueError(f"Missing required parameter: '{field}'")

    # Validate URL
    url = urlparse(unquote(params["source"]))
    if not url.scheme or not url.netloc:
        raise ValueError(f"Invalid URL provided: '{params['source']}'")

    # Validate integer parameters
    try:
        header_offset = int(params["header_offset"])
        compression_method = int(params["compression_method"])
        compress_size = int(params["compress_size"])
    except ValueError:
        raise ValueError("header_offset, compression_method, and compress_size must be integers.")

    return FileExtractParameters(
        source=params["source"],
        header_offset=header_offset,
        compression_method=compression_method,
        compress_size=compress_size,
    )


def get_final_url(url: str):
    """Follow redirects and return the final URL."""
    session = requests.Session()
    response = session.head(url, allow_redirects=True)
    return response.url


def get_range(url: str, start: int, length: int):
    """Fetch a specific byte range from a remote file."""
    headers = {"Range": f"bytes={start}-{start + length - 1}"}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    return response


def calculate_file_data_offset(url, header_offset: int):
    """Determine the offset of the file data inside the ZIP archive."""
    stream_response = get_range(url, header_offset, 30)
    local_header_data = stream_response.content
    file_name_length, extra_field_length = unpack("<HH", local_header_data[26:30])
    return header_offset + 30 + file_name_length + extra_field_length


def stream_and_decompress(file_extract_params: FileExtractParameters, output_file: str):
    """Stream a file from a ZIP archive hosted remotely using byte-range requests."""
    final_url = get_final_url(file_extract_params.source)

    # Calculate actual start of file data
    file_data_offset = calculate_file_data_offset(final_url, file_extract_params.header_offset)
    response_stream = get_range(final_url, file_data_offset, file_extract_params.compress_size)

    if file_extract_params.compression_method == 0:  # Stored (no compression)
        with open(output_file, "wb") as f:
            for chunk in response_stream.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_file

    if file_extract_params.compression_method == 8:  # Deflate
        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    else:
        raise ValueError(f"Unsupported compression method: {file_extract_params.compression_method}")

    with open(output_file, "wb") as f:
        for chunk in response_stream.iter_content(chunk_size=8192):
            if chunk:
                f.write(decompressor.decompress(chunk))

        # Flush remaining decompressed data
        f.write(decompressor.flush())

    return output_file


__all__ = ("RemoteZipFilesSource",)
