"""Observe one dataset blocking tool execution, without loading its ORM object."""

from collections.abc import Iterable
from typing import (
    Any,
    NamedTuple,
)

from sqlalchemy import (
    ColumnElement,
    func,
    Label,
    select,
)
from sqlalchemy.orm import Session

from galaxy.model import (
    Dataset,
    DatasetCollection,
    HistoryDatasetAssociation,
    required_object_session,
)

SNAPSHOT_BATCH_SIZE = 500
NON_READY = "non_ready"


class ReadinessSnapshot(NamedTuple):
    state: str | None
    extension: str
    deleted: bool
    dataset_deleted: bool


def _readiness(state: str | None, extension: str, deleted: bool, dataset_deleted: bool | None) -> ReadinessSnapshot:
    # Moving between non-ready states (queued -> running) cannot unblock a wait.
    if state in Dataset.non_ready_states:
        state = NON_READY
    return ReadinessSnapshot(state, extension, deleted, bool(dataset_deleted))


def dataset_readiness(dataset: HistoryDatasetAssociation) -> ReadinessSnapshot:
    assert dataset.dataset is not None
    return _readiness(dataset.state, dataset.extension, dataset.deleted, dataset.dataset.deleted)


def _effective_state() -> ColumnElement[Any]:
    return func.coalesce(HistoryDatasetAssociation._state, Dataset.state)


def _snapshot_columns() -> tuple[Label[Any], Label[Any]]:
    return (
        _effective_state().label("effective_state"),
        func.coalesce(Dataset.deleted, False).label("dataset_deleted"),
    )


def _row_readiness(row: Any) -> ReadinessSnapshot:
    return _readiness(row.effective_state, row.extension, row.deleted, row.dataset_deleted)


def readiness_snapshots(session: Session, hda_ids: Iterable[int]) -> dict[int, ReadinessSnapshot]:
    """Current snapshots keyed by HDA id; ids without a row are absent."""
    ids = list(hda_ids)
    snapshots: dict[int, ReadinessSnapshot] = {}
    for start in range(0, len(ids), SNAPSHOT_BATCH_SIZE):
        stmt = (
            select(
                HistoryDatasetAssociation.id,
                HistoryDatasetAssociation.extension,
                HistoryDatasetAssociation.deleted,
                *_snapshot_columns(),
            )
            .join(Dataset)
            .where(HistoryDatasetAssociation.id.in_(ids[start : start + SNAPSHOT_BATCH_SIZE]))
        )
        for row in session.execute(stmt):
            snapshots[row.id] = _row_readiness(row)
    return snapshots


def blocking_dataset(
    collection: DatasetCollection,
    states: Iterable[str] | None = None,
    extensions: Iterable[str] | None = None,
) -> tuple[int, ReadinessSnapshot] | None:
    stmt = collection._build_nested_collection_attributes_stmt(hda_attributes=("id", "extension", "deleted"))
    stmt = stmt.add_columns(*_snapshot_columns()).order_by(None)
    if states is not None:
        stmt = stmt.where(_effective_state().in_(states))
    if extensions is not None:
        stmt = stmt.where(HistoryDatasetAssociation.extension.in_(extensions))
    row = required_object_session(collection).execute(stmt.limit(1)).first()
    if row is None:
        return None
    return row.id, _row_readiness(row)
