"""Observe one dataset blocking tool execution, without loading its ORM object."""

from collections.abc import Iterable
from typing import NamedTuple

from sqlalchemy import func

from galaxy.model import (
    Dataset,
    DatasetCollection,
    HistoryDatasetAssociation,
    required_object_session,
)


class ReadinessSnapshot(NamedTuple):
    state: str | None
    extension: str
    deleted: bool
    dataset_deleted: bool


def dataset_readiness(dataset: HistoryDatasetAssociation) -> ReadinessSnapshot:
    assert dataset.dataset is not None
    return ReadinessSnapshot(dataset.state, dataset.extension, dataset.deleted, bool(dataset.dataset.deleted))


def blocking_dataset(
    collection: DatasetCollection,
    states: Iterable[str] | None = None,
    extensions: Iterable[str] | None = None,
) -> tuple[int, ReadinessSnapshot] | None:
    state = func.coalesce(HistoryDatasetAssociation._state, Dataset.state)
    stmt = collection._build_nested_collection_attributes_stmt(hda_attributes=("id", "extension", "deleted"))
    stmt = stmt.add_columns(
        state.label("effective_state"), func.coalesce(Dataset.deleted, False).label("dataset_deleted")
    ).order_by(None)
    if states is not None:
        stmt = stmt.where(state.in_(states))
    if extensions is not None:
        stmt = stmt.where(HistoryDatasetAssociation.extension.in_(extensions))
    row = required_object_session(collection).execute(stmt.limit(1)).first()
    if row is None:
        return None
    return row.id, ReadinessSnapshot(row.effective_state, row.extension, row.deleted, row.dataset_deleted)
