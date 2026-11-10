"""Dependencies shared by tool input checks and workflow scheduling."""

from collections.abc import (
    Collection,
    Iterable,
)
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    TypeAlias,
)

from galaxy.exceptions import ToolInputsNotReadyException
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    DatasetInstance,
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


class ToolInputsNotReadyWithDependencies(ToolInputsNotReadyException):
    """An input wait with dependencies the workflow scheduler can observe."""

    def __init__(
        self,
        err_msg: str | None = None,
        type: str = "info",
        *,
        dependencies: Iterable[SchedulingDependency],
        **extra_error_info: Any,
    ) -> None:
        super().__init__(err_msg, type, **extra_error_info)
        self.dependencies = tuple(dependencies)


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


def dataset_dependencies(dataset: DatasetInstance) -> list[SchedulingDependency]:
    """Track a dataset the caller already found blocking."""
    if not isinstance(dataset, HistoryDatasetAssociation) or not dataset.id:
        return []
    return [SchedulingDependency(DependencyType.HDA, dataset.id, dataset_readiness(dataset))]


ReadinessInput: TypeAlias = DatasetInstance | DatasetCollection | DatasetCollectionElement | CollectionAdapter


def input_readiness_dependencies(
    value: ReadinessInput,
    *,
    states: Collection[str],
    extensions: Collection[str] | None = None,
) -> list[SchedulingDependency]:
    """Track one member in ``states``; the next evaluation can discover the remaining waits."""
    if isinstance(value, DatasetCollection) and value.id:
        blocker = blocking_dataset(value, states, extensions)
        if blocker is None:
            return []
        hda_id, readiness = blocker
        return [SchedulingDependency(DependencyType.HDA, hda_id, readiness)]
    if isinstance(value, DatasetInstance):
        if value.state not in states or (extensions is not None and value.extension not in extensions):
            return []
        return dataset_dependencies(value)
    if isinstance(value, DatasetCollectionElement):
        member = value.child_collection or value.hda
        return input_readiness_dependencies(member, states=states, extensions=extensions) if member else []
    values: Iterable[Any]
    if isinstance(value, CollectionAdapter):
        adapting = value.adapting
        if not isinstance(adapting, list):
            return input_readiness_dependencies(adapting, states=states, extensions=extensions)
        values = (element.hda for element in adapting)
    else:
        values = value.elements
    for element in values:
        dependencies = input_readiness_dependencies(element, states=states, extensions=extensions)
        if dependencies:
            return dependencies
    return []
