from typing import Optional

from galaxy.tool_util.parser.parameter_validators import parse_xml_validators
from galaxy.tool_util.unittest_utils.sample_data import (
    INVALID_XML_VALIDATORS,
    VALID_XML_VALIDATORS,
)
from galaxy.util import XML


def test_xml_validation_valid():
    for xml_validator in VALID_XML_VALIDATORS:
        _validate_xml_str(xml_validator)


def test_xml_validation_invalid():
    for xml_validator in INVALID_XML_VALIDATORS:
        exc: Optional[Exception] = None
        try:
            _validate_xml_str(xml_validator)
        except ValueError as e:
            exc = e
        assert exc is not None, f"{xml_validator} - validated when it wasn't expected to"


def _validate_xml_str(xml_str: str):
    xml_el = XML(f"<param>{xml_str}</param>")
    parse_xml_validators(xml_el)
