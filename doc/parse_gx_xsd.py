# TODO: Add examples, tables and best practice links to command
# TODO: Examples of truevalue, falsevalue
# TODO: Test param extra_file
# Things dropped from schema_template.md (still documented inside schema).
#  - request_parameter_translation

import sys
from io import StringIO

from lxml import etree

with open(sys.argv[2]) as f:
    xmlschema_doc = etree.parse(f)

markdown_buffer = StringIO()


def main():
    """Entry point for the function that builds Markdown help for the Galaxy XSD."""
    toc_list = []
    content_list = []
    found_tag = False
    with open(sys.argv[1]) as markdown_template:
        for line in markdown_template:
            if line.startswith("$tag:"):
                found_tag = True
                tag = Tag(line.rstrip())
                toc_list.append(tag.build_toc_entry())
                content_list.append(tag.build_help())
            elif not found_tag:
                print(line, end="")
            else:
                raise Exception("No normal text allowed after the first $tag")
    print("## Contents\n")
    for el in toc_list:
        print(el)
    print("\n")
    for el in content_list:
        print(el, end="")


class Tag:
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
        for _ in ["|", "_"]:
            anchor = anchor.replace(_, "-")
        return "#" + anchor

    @property
    def _pretty_title(self):
        return " > ".join("``%s``" % p for p in self.title.split("|"))

    def build_toc_entry(self):
        return f"* [{self._pretty_title}]({self._anchor})"

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
    text = _replace_attribute_list(tag, text, attributes)
    for line in text.splitlines():
        if line.startswith("$assertions"):
            assertions_tag = xmlschema_doc.find(
                "//{http://www.w3.org/2001/XMLSchema}complexType[@name='TestAssertions']"
            )
            assertions_buffer = StringIO()
            assertions_buffer.write(_doc_or_none(assertions_tag))
            assertions_buffer.write("\n\n")

            assertion_groups = assertions_tag.xpath(
                "xs:choice/xs:group", namespaces={"xs": "http://www.w3.org/2001/XMLSchema"}
            )
            for group in assertion_groups:
                ref = group.attrib["ref"]
                assertion_tag = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}group[@name='" + ref + "']")
                doc = _doc_or_none(assertion_tag)
                assertions_buffer.write(f"### {doc}\n\n")
                elements = assertion_tag.findall(
                    "{http://www.w3.org/2001/XMLSchema}choice/{http://www.w3.org/2001/XMLSchema}element"
                )
                for element in elements:
                    doc = _doc_or_none(element)
                    if doc is None:
                        doc = _doc_or_none(_type_el(element))
                    assert doc is not None, "Documentation for %s is empty" % element.attrib["name"]
                    doc = doc.strip()

                    element_el = _find_tag_el(element)
                    element_attributes = _find_attributes(element_el)
                    doc = _replace_attribute_list(element_el, doc, element_attributes)
                    assertions_buffer.write(f"#### ``{element.attrib['name']}``:\n\n{doc}\n\n")
            text = text.replace(line, assertions_buffer.getvalue())
    tag_help.write(text)
    best_practices = _get_bp_link(annotation_el)
    if best_practices:
        tag_help.write("\n\n### Best Practices\n")
        tag_help.write(
            """
Find the Intergalactic Utilities Commision suggested best practices for this
element [here](%s)."""
            % best_practices
        )
    tag_help.write(_build_attributes_table(tag, attributes, hide_attributes))

    return tag_help.getvalue()


def _replace_attribute_list(tag, text, attributes):
    for line in text.splitlines():
        if not line.startswith("$attribute_list:"):
            continue
        attributes_str, header_level = line.split(":")[1:3]
        if attributes_str == "":
            attribute_names = None
        else:
            attribute_names = attributes_str.split(",")
        header_level = int(header_level)
        text = text.replace(
            line, _build_attributes_table(tag, attributes, attribute_names=attribute_names, header_level=header_level)
        )
    return text


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
        header_prefix = "#" * header_level
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
            details = details.replace("\n", " ").strip()
            best_practices = _get_bp_link(annotation_el)
            if best_practices:
                details += (
                    """ Find the Intergalactic Utilities Commision suggested best practices for this element [here](%s)."""
                    % best_practices
                )

            attribute_table.write(f"``{name}`` | {details} | {use}\n")
    return attribute_table.getvalue()


def _find_attributes(tag):
    raw_attributes = (
        tag.findall("{http://www.w3.org/2001/XMLSchema}attribute")
        or tag.findall("{http://www.w3.org/2001/XMLSchema}complexType/{http://www.w3.org/2001/XMLSchema}attribute")
        or tag.findall(
            "{http://www.w3.org/2001/XMLSchema}complexContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attribute"
        )
        or tag.findall(
            "{http://www.w3.org/2001/XMLSchema}simpleContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attribute"
        )
    )
    attribute_groups = (
        tag.findall("{http://www.w3.org/2001/XMLSchema}attributeGroup")
        or tag.findall("{http://www.w3.org/2001/XMLSchema}complexType/{http://www.w3.org/2001/XMLSchema}attributeGroup")
        or tag.findall(
            "{http://www.w3.org/2001/XMLSchema}complexContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attributeGroup"
        )
        or tag.findall(
            "{http://www.w3.org/2001/XMLSchema}simpleContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}attributeGroup"
        )
    )
    attributes = list(raw_attributes)
    for attribute_group in attribute_groups:
        attribute_group_name = attribute_group.get("ref")
        attribute_group_def = xmlschema_doc.find(
            "//{http://www.w3.org/2001/XMLSchema}attributeGroup/[@name='%s']" % attribute_group_name
        )
        attributes.extend(_find_attributes(attribute_group_def))
    return attributes


def _find_tag_el(tag):
    if _doc_or_none(tag) is not None:
        return tag

    return _type_el(tag)


def _type_el(tag):
    element_type = tag.attrib["type"]
    type_el = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}complexType/[@name='%s']" % element_type)
    if type_el is None:
        type_el = xmlschema_doc.find("//{http://www.w3.org/2001/XMLSchema}simpleType/[@name='%s']" % element_type)
    return type_el


def _doc_or_none(tag):
    doc_el = tag.find("{http://www.w3.org/2001/XMLSchema}annotation/{http://www.w3.org/2001/XMLSchema}documentation")
    if doc_el is None:
        return None
    else:
        return doc_el.text


if __name__ == "__main__":
    main()
