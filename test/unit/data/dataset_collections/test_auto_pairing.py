from dataclasses import dataclass
from typing import (
    Dict,
    List,
)

import yaml
from pydantic import (
    BaseModel,
    RootModel,
)

from galaxy.model.dataset_collections.auto_pairing import auto_pair
from galaxy.util.resources import resource_string


@dataclass
class MockDataset:
    name: str


class PairedItem(BaseModel):
    forward: str
    reverse: str


class AutoPairingSpecItem(BaseModel):
    doc: str
    inputs: List[str]
    paired: Dict[str, PairedItem]


AutoPairingSpecification = RootModel[List[AutoPairingSpecItem]]


def test_auto_pairing_specification():
    auto_pairing_specification = resource_string("galaxy.model.dataset_collections", "auto_pairing_spec.yml")
    auto_pairing_specification_dicts = yaml.safe_load(auto_pairing_specification)
    tests = AutoPairingSpecification.model_validate(auto_pairing_specification_dicts)
    for test in tests.root:
        inputs = [MockDataset(name) for name in test.inputs]
        summary = auto_pair(inputs)
        pairs = summary.paired
        for name, expected_pair in test.paired.items():
            pair = next((p for p in pairs if p.name == name), None)
            assert pair is not None, f"Pair {name} not found"
            assert pair.forward.name == expected_pair.forward, f"Forward mismatch for pair {name}"
            assert pair.reverse.name == expected_pair.reverse, f"Reverse mismatch for pair {name}"
