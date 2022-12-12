"""
Location of protocols used in datatypes
"""

from typing import Any

from typing_extensions import Protocol


class GeneratePrimaryFileDataset(Protocol):
    extra_files_path: str
    metadata: Any
