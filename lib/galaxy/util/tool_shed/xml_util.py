import io
import logging
import os
import tempfile
from xml.etree import ElementTree as XmlET

from galaxy.util import (
    xml_to_string
)

log = logging.getLogger(__name__)


class Py27CommentedTreeBuilder(XmlET.TreeBuilder):

    def doctype(*args):
        # handle deprecation warning for XMLParsing a file with DOCTYPE
        pass

    def comment(self, data):
        self.start(XmlET.Comment, {})
        self.data(data)
        self.end(XmlET.Comment)


def create_and_write_tmp_file(elem):
    tmp_str = xml_to_string(elem, pretty=True)
    with tempfile.NamedTemporaryFile(prefix="tmp-toolshed-cawrf", delete=False) as fh:
        tmp_filename = fh.name
    with io.open(tmp_filename, mode='w', encoding='utf-8') as fh:
        fh.write(tmp_str)
    return tmp_filename


def create_element(tag, attributes=None, sub_elements=None):
    """
    Create a new element whose tag is the value of the received tag, and whose attributes are all
    key / value pairs in the received attributes and sub_elements.
    """
    if tag:
        elem = XmlET.Element(tag)
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
                    if k == 'packages':
                        # The received sub_elements is an odict whose key is 'packages' and whose
                        # value is a list of ( name, version ) tuples.
                        for v_tuple in v:
                            sub_elem = XmlET.SubElement(elem, 'package')
                            sub_elem_name, sub_elem_version = v_tuple
                            sub_elem.set('name', sub_elem_name)
                            sub_elem.set('version', sub_elem_version)
                    elif isinstance(v, list):
                        sub_elem = XmlET.SubElement(elem, k)
                        # If v is a list, then it must be a list of tuples where the first
                        # item is the tag and the second item is the text value.
                        for v_tuple in v:
                            if len(v_tuple) == 2:
                                v_tag = v_tuple[0]
                                v_text = v_tuple[1]
                                # Don't include fields that are blank.
                                if v_text:
                                    v_elem = XmlET.SubElement(sub_elem, v_tag)
                                    v_elem.text = v_text
                    else:
                        sub_elem = XmlET.SubElement(elem, k)
                        sub_elem.text = v
        return elem
    return None


def parse_xml(file_name):
    """Returns a parsed xml tree with comments intact."""
    error_message = ''
    if not os.path.exists(file_name):
        return None, "File does not exist %s" % str(file_name)

    with open(file_name, 'r') as fobj:
        try:
            tree = XmlET.parse(fobj, parser=XmlET.XMLParser(target=Py27CommentedTreeBuilder()))
        except Exception as e:
            error_message = "Exception attempting to parse %s: %s" % (str(file_name), str(e))
            log.exception(error_message)
            return None, error_message
    return tree, error_message
