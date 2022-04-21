import logging
import os
import tempfile

from galaxy.util import etree
from galaxy.util import parse_xml as galaxy_parse_xml
from galaxy.util import (
    unicodify,
    xml_to_string,
)

log = logging.getLogger(__name__)


def create_and_write_tmp_file(elem):
    tmp_str = xml_to_string(elem, pretty=True)
    with tempfile.NamedTemporaryFile(prefix="tmp-toolshed-cawrf", delete=False) as fh:
        tmp_filename = fh.name
    with open(tmp_filename, mode="w", encoding="utf-8") as fh:
        fh.write(tmp_str)
    return tmp_filename


def create_element(tag, attributes=None, sub_elements=None):
    """
    Create a new element whose tag is the value of the received tag, and whose attributes are all
    key / value pairs in the received attributes and sub_elements.
    """
    if tag:
        elem = etree.Element(tag)
        if attributes:
            # The received attributes is an odict to preserve ordering.
            for k, v in attributes.items():
                elem.set(k, v)
        if sub_elements:
            # The received attributes is an odict.  These handle information that tends to be
            # long text including paragraphs (e.g., description and long_description.
            for k, v in sub_elements.items():
                # Don't include fields that are blank.
                if v:
                    if k == "packages":
                        # The received sub_elements is an odict whose key is 'packages' and whose
                        # value is a list of ( name, version ) tuples.
                        for v_tuple in v:
                            sub_elem = etree.SubElement(elem, "package")
                            sub_elem_name, sub_elem_version = v_tuple
                            sub_elem.set("name", sub_elem_name)
                            sub_elem.set("version", sub_elem_version)
                    elif isinstance(v, list):
                        sub_elem = etree.SubElement(elem, k)
                        # If v is a list, then it must be a list of tuples where the first
                        # item is the tag and the second item is the text value.
                        for v_tuple in v:
                            if len(v_tuple) == 2:
                                v_tag = v_tuple[0]
                                v_text = v_tuple[1]
                                # Don't include fields that are blank.
                                if v_text:
                                    v_elem = etree.SubElement(sub_elem, v_tag)
                                    v_elem.text = v_text
                    else:
                        sub_elem = etree.SubElement(elem, k)
                        sub_elem.text = v
        return elem
    return None


def parse_xml(file_name, check_exists=True):
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
    "create_element",
    "parse_xml",
)
