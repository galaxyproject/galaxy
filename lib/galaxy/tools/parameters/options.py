from typing import (
    NamedTuple,
    Optional,
)

from galaxy.model import (
    DatasetInstance,
    HistoryDatasetAssociation,
)
from galaxy.security.idencoding import IdEncodingHelper


class ParameterOption(NamedTuple):
    name: str
    value: str
    selected: bool = False
    dataset: Optional["DatasetInstance"] = None

    def serialize(self, security: "IdEncodingHelper"):
        if self.dataset:
            return (
                self.name,
                {
                    "src": "hda" if isinstance(self.dataset, HistoryDatasetAssociation) else "ldda",
                    "id": security.encode_id(self.dataset.id),
                },
                self.selected,
            )
        return (self.name, self.value, self.selected)
