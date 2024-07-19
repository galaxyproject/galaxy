"""Types used by interactor and test case processor."""

from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

ExtraFileInfoDictT = Dict[str, Any]
RequiredFileTuple = Tuple[str, ExtraFileInfoDictT]
RequiredFilesT = List[RequiredFileTuple]
RequiredDataTablesT = List[str]
RequiredLocFileT = List[str]
