# coding: utf-8
# TODO: Add examples, tables and best practice links to command
# TODO: Examples of truevalue, falsevalue
# TODO: Test param extra_file
# Things dropped from schema_template.md (still documented inside schema).
#  - request_parameter_translation
from __future__ import print_function

import sys

from lxml import etree
from six import StringIO

with open(sys.argv[2], "r") as f:
    xmlschema_doc = etree.parse(f)

markdown_buffer = StringIO()


def main():
    """Entry point for the function that builds Markdown help for the Galaxy XSD."""
    toc_list = []
    content_list = []
    found_tag = False
    with open(sys.argv[1], "r") as markdown_template:
        for line in markdown_template:
            if line.startswith("$tag:"):
                found_tag = True
                tag = Tag(line.rstrip())
                toc_list.append(tag.build_toc_entry())
                content_list.append(tag.build_help())
            elif not found_tag:
                print(line, end='')
            else:
                raise Exception("No normal text allowed after the first $tag")
    print("## Contents\n")
    for el in toc_list:
        print(el)
    print("\n")
    for el in content_list:
        print(el, end='')


class Tag(object):

    def __init__(self, line):
        assert line.startswith("$tag:")
        line_parts = line.split(" ")
        first_part = line_parts[0]
        hide_attributes = False
        if len(line_parts) > 1:
            if "hide_attributes" in line_parts[1]:
                hide_attributes = True
        _, title, xpath = first_part.split(":")
        xpath = xpath.replace("/element", "/{http://www.w3.org/2001/XMLSchema}element")
        xpath = xpath.replace("/group", "/{http://www.w3.org/2001/XMLSchema}group")
        xpath = xpath.replace("/complexType", "/{http://www.w3.org/2001/XMLSchema}complexType")
        self.xpath = xpath
        self.hide_attributes = hide_attributes
        self.title = title

    @property
    def _anchor(self):
        anchor = self.title
        for _ in ['|', '_']:
            anchor = anchor.replace(_, '-')
        return '#' + anchor

    @property
    def _pretty_title(self):
        return " > ".join(["``%s``" % p for p in self.title.split("|")])

    def build_toc_entry(self):
        return "* [%s](%s)" % (self._pretty_title, self._anchor)

    def build_help(self):
        tag = xmlschema_doc.find(self.xpath)
        if tag is None:
            raise Exception("Could not find xpath for %s" % self.xpath)

        tag_help = StringIO()
        tag_help.write("## " + self._pretty_title)
        tag_help.write("\n\n")
        tag_help.write(_build_tag(tag, self.hide_attributes))
        tag_help.write("\n\n")
        return tag_help.getvalue()


def _build_tag(tag, hide_attributes):
    tag_el = _find_tag_el(tag)
    attributes = _find_attributes(tag)
    tag_help = StringIO()
    annotation_el = tag_el.find("{http://www.w3.org/2001/XMLSchema}annotation")
    text = annotation_el.find("{http://www.w3.org/2001/XMLSchema}documentation").text
    for line in text.splitlines():
        if line.startswith("$attribute_list:"):
            attributes_str, header_level = line.split(":")[1:3]
            attribute_names = attributes_str.split(",")
            header_level = int(header_level)
            text = text.replace(line, _build_attributes_table(tag, attributes, attribute_names=attribute_names, header_level=header_level))
        if line.startswith("$assertions"):
            assertions_tag = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}complexType[@name='TestAssertions']")
            assertion_tag = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}group[@name='TestAssertion']")
            assertions_buffer = StringIO()
            assertions_buffer.write(_doc_or_none(assertions_tag))
            assertions_buffer.write("\n\n")
            assertions_buffer.write("Child Element/Assertion | Details \n")
            assertions_buffer.write("--- | ---\n")
            elements = assertion_tag.findall("{http://www.w3.org/2001/XMLSchema}choice/{http://www.w3.org/2001/XMLSchema}element")
            for element in elements:
                doc = _doc_or_none(element)
                if doc is None:
                    doc = _doc_or_none(_type_el(element))
                assert doc is not None, "Documentation for %s is empty" % element.attrib["name"]
                doc = doc.strip()
                assertions_buffer.write("``%s`` | %s\n" % (element.attrib["name"], doc))
            text = text.replace(line, assertions_buffer.getvalue())
    tag_help.write(text)
    best_practices = _get_bp_link(annotation_el)
    if best_practices:
        tag_help.write("\n\n### Best Practices\n")
        tag_help.write("""
Find the Intergalactic Utilities Commision suggested best practices for this
element [here](%s).""" % best_practices)
    tag_help.write(_build_attributes_table(tag, attributes, hide_attributes))

    return tag_help.getvalue()


def _get_bp_link(annotation_el):
    anchor = annotation_el.attrib.get("{http://galaxyproject.org/xml/1.0}best_practices", None)
    link = None
    if anchor:
        link = "https://planemo.readthedocs.io/en/latest/standards/docs/best_practices/tool_xml.html#%s" % anchor
    return link


def _build_attributes_table(tag, attributes, hide_attributes=False, attribute_names=None, header_level=3):
    attribute_table = StringIO()
    attribute_table.write("\n\n")
    if attributes and not hide_attributes:
        header_prefix = '#' * header_level
        attribute_table.write("\n%s Attributes\n\n" % header_prefix)
        attribute_table.write("Attribute | Details | Required\n")
        attribute_table.write("--- | --- | ---\n")
        for attribute in attributes:
            name = attribute.attrib["name"]
            if attribute_names and name not in attribute_names:
                continue
            details = _doc_or_none(attribute)
            if details is None:
                type_el = _type_el(attribute)
                assert type_el is not None, "No details or type found for %s" % name
                details = _doc_or_none(type_el)
                annotation_el = type_el.find("{http://www.w3.org/2001/XMLSchema}annotation")
            else:
                annotation_el = attribute.find("{http://www.w3.org/2001/XMLSchema}annotation")

            use = attribute.attrib.get("use", "optional") == "required"
            if "|" in details:
                # This seems to work fine for now, but potentially can cause problems.
                pass
            details = details.replace("\n", " ").strip()
            best_practices = _get_bp_link(annotation_el)
            if best_practices:
                details += """ Find the Intergalactic Utilities Commision suggested best practices for this element [here](%s).""" % best_practices

            attribute_table.write("``%s`` | %s | %s\n" % (name, details, use))
    return attribute_table.getvalue()


def _find_attributes(tag):
    return tag.findall("{http://www.w3.org/2001/XMLSchema}attribute") or \
        tag.findall("{http://www.w3.org/2001/XMLSchema}complexType/{http://www.w3.org/2001/XMLSchema}attribute") or \
        tag.findall("{http://www.w3.org/2001/XMLSchema}complexContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attribute") or \
        tag.findall("{http://www.w3.org/2001/XMLSchema}simpleContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attribute")


def _find_tag_el(tag):
    if _doc_or_none(tag) is not None:
        return tag

    return _type_el(tag)


def _type_el(tag):
    element_type = tag.attrib["type"]
    type_el = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}complexType/[@name='%s']" % element_type) or \
        xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}simpleType/[@name='%s']" % element_type)
    return type_el


def _doc_or_none(tag):
    doc_el = tag.find("{http://www.w3.org/2001/XMLSchema}annotation/{http://www.w3.org/2001/XMLSchema}documentation")
    if doc_el is None:
        return None
    else:
        return doc_el.text


if __name__ == '__main__':
    main()
