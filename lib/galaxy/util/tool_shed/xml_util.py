import logging
import os
import tempfile
from typing import (
    Optional,
    Tuple,
)

from galaxy.util import (
    etree,
    parse_xml as galaxy_parse_xml,
    unicodify,
    xml_to_string,
)
from galaxy.util.path import StrPath

log = logging.getLogger(__name__)


def create_and_write_tmp_file(elem: etree.Element) -> str:
    tmp_str = xml_to_string(elem, pretty=True)
    with tempfile.NamedTemporaryFile(prefix="tmp-toolshed-cawrf", delete=False) as fh:
        tmp_filename = fh.name
    with open(tmp_filename, mode="w", encoding="utf-8") as fh:
        fh.write(tmp_str)
    return tmp_filename


def parse_xml(file_name: StrPath, check_exists=True) -> Tuple[Optional[etree.ElementTree], str]:
    """Returns a parsed xml tree with comments intact."""
    error_message = ""
    if check_exists and not os.path.exists(file_name):
        return None, f"File does not exist {str(file_name)}"
    try:
        tree = galaxy_parse_xml(file_name, remove_comments=False, strip_whitespace=False)
    except OSError:
        raise
    except Exception as e:
        error_message = f"Exception attempting to parse {str(file_name)}: {unicodify(e)}"
        log.exception(error_message)
        return None, error_message
    return tree, error_message


__all__ = (
    "create_and_write_tmp_file",
    "parse_xml",
)
