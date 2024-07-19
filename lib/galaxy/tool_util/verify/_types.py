"""Types used by interactor and test case processor."""

from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

# inputs that have been processed with parse.py and expanded out
ExpandedToolInputs = Dict[str, Any]
# ExpandedToolInputs where any model objects have been json-ified with to_dict()
ExpandedToolInputsJsonified = Dict[str, Any]
ExtraFileInfoDictT = Dict[str, Any]
RequiredFileTuple = Tuple[str, ExtraFileInfoDictT]
RequiredFilesT = List[RequiredFileTuple]
RequiredDataTablesT = List[str]
RequiredLocFileT = List[str]
