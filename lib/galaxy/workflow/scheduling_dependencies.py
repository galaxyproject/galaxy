"""Dependencies shared by tool input checks and workflow scheduling."""

from collections.abc import (
    Collection,
    Iterable,
)
from dataclasses import dataclass
from enum import Enum
from typing import Any

from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
)
from galaxy.model.dataset_collections.adapters import CollectionAdapter
from galaxy.model.dataset_collections.readiness import (
    blocking_dataset,
    dataset_readiness,
    ReadinessSnapshot,
)


class DependencyType(str, Enum):
    JOB = "job"
    HDA = "hda"
    DATASET_COLLECTION = "dataset_collection"
    WORKFLOW_INVOCATION_STEP = "workflow_invocation_step"


@dataclass(frozen=True)
class SchedulingDependency:
    dependency_type: DependencyType
    id: int
    # Input readiness waits wake on a change to the values that caused the wait,
    # including failures and paused states, rather than collection population.
    readiness: ReadinessSnapshot | None = None


@dataclass(frozen=True)
class SchedulingDependencies:
    """What the next scheduling attempt of an invocation waits on."""

    tracked: frozenset[SchedulingDependency]
    untracked: tuple[str, ...]
    # The iteration stopped before scheduling everything it could.
    more_work: bool


def unpopulated_collection_dependencies(collection: DatasetCollection) -> list[SchedulingDependency]:
    return [
        SchedulingDependency(DependencyType.DATASET_COLLECTION, collection_id)
        for collection_id in collection.unpopulated_collection_ids()
    ]


def input_readiness_dependencies(
    value: Any,
    *,
    states: Collection[str] | None = None,
    extensions: Collection[str] | None = None,
) -> list[SchedulingDependency]:
    """Track one blocker; the next evaluation can discover the remaining waits."""
    if isinstance(value, DatasetCollection) and value.id:
        blocker = blocking_dataset(value, states, extensions)
        if blocker is None:
            return []
        hda_id, readiness = blocker
        return [SchedulingDependency(DependencyType.HDA, hda_id, readiness)]
    if isinstance(value, HistoryDatasetAssociation):
        if not value.id or (states is not None and value.state not in states):
            return []
        if extensions is not None and value.extension not in extensions:
            return []
        return [SchedulingDependency(DependencyType.HDA, value.id, dataset_readiness(value))]
    if isinstance(value, DatasetCollectionElement):
        return input_readiness_dependencies(value.child_collection or value.hda, states=states, extensions=extensions)
    values: Iterable[Any]
    if isinstance(value, CollectionAdapter):
        adapting = value.adapting
        if not isinstance(adapting, list):
            return input_readiness_dependencies(adapting, states=states, extensions=extensions)
        values = (element.hda for element in adapting)
    elif isinstance(value, DatasetCollection):
        values = value.elements
    else:
        return []
    for element in values:
        dependencies = input_readiness_dependencies(element, states=states, extensions=extensions)
        if dependencies:
            return dependencies
    return []
