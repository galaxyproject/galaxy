"""Code around assigning implicit list identifiers for collections."""

import os.path
from typing import (
    List,
    Optional,
    Set,
    Tuple,
)
from urllib.parse import urlparse

from pydantic import BaseModel


class FillIdentifiers(BaseModel):
    fill_inner_list_identifiers: bool = False
    deduplication_pattern: str = "_{#}"
    deduplication_index_from: int = 1


def filename_to_element_identifier(filename_or_uri: str):
    basename = guess_filename_from_url(filename_or_uri)
    for zip_extension in [".zip", ".tar.gz", ".tar", ".tgz", ".gz", "bz2", ".bz"]:
        if basename.endswith(zip_extension):
            basename = basename[: -len(zip_extension)]
    if "." in basename:
        basename = basename.split(".")[0]
    return basename


def fill_in_identifiers(
    uris_to_identifiers: List[Tuple[str, Optional[str]]], config: Optional[FillIdentifiers]
) -> List[Optional[str]]:
    if config is None:
        config = FillIdentifiers()

    new_identifiers: List[Optional[str]] = []
    seen_identifiers: Set[Optional[str]] = set()
    for uri, identifier in uris_to_identifiers:
        if identifier is None and config.fill_inner_list_identifiers:
            basename = filename_to_element_identifier(uri)
            identifier = basename
            assert identifier
            if identifier in seen_identifiers:
                # Handle deduplication
                index = config.deduplication_index_from
                suffix = config.deduplication_pattern.replace("{#}", str(index))
                new_identifier = f"{basename}{suffix}"
                while new_identifier in seen_identifiers:
                    index += 1
                    new_identifier = f"{basename}{config.deduplication_pattern.format(index=index)}"
                identifier = new_identifier
            seen_identifiers.add(identifier)
            new_identifiers.append(identifier)
        else:
            seen_identifiers.add(identifier)
            new_identifiers.append(identifier)

    return new_identifiers


def guess_filename_from_url(url: str) -> str:
    """
    Guess the filename for a given URL.

    :param url: The URL to extract the filename from.
    :return: The guessed filename.
    """
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    return filename or ""
