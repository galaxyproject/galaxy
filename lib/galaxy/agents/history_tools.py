"""
History data access helpers for the page assistant agent.

Standalone functions using direct SQLAlchemy queries via session parameter.
Designed for MCP reuse: string inputs, string outputs, no Galaxy manager dependencies.
"""

import logging
import re
from collections.abc import Callable
from typing import (
    Optional,
    Union,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


async def list_history_items(
    session: Session,
    history_id: int,
    offset: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    include_hidden: bool = False,
    encode_id: Optional[Callable[[int], str]] = None,
) -> str:
    """List datasets and collections in a history, ordered by HID.

    Returns a compact one-line-per-item format suitable for LLM consumption.
    """
    from galaxy.model import (
        Dataset,
        DatasetCollection as DC,
        HistoryDatasetAssociation as HDA,
        HistoryDatasetCollectionAssociation as HDCA,
    )

    limit = min(limit, 200)

    hda_rows = session.execute(
        select(
            HDA.id,
            HDA.hid,
            HDA.name,
            HDA.extension,
            HDA._state,
            HDA.deleted,
            HDA.visible,
            Dataset.file_size,
        )
        .join(Dataset, HDA.dataset_id == Dataset.id)
        .where(HDA.history_id == history_id)
    ).all()

    hdca_rows = session.execute(
        select(HDCA.id, HDCA.hid, HDCA.name, DC.collection_type, HDCA.deleted, HDCA.visible)
        .join(DC, HDCA.collection_id == DC.id)
        .where(HDCA.history_id == history_id)
    ).all()

    _enc = encode_id or str

    items = []
    for hda_row in hda_rows:
        item_id, hid, name, ext, state, deleted, visible, file_size = hda_row
        if not include_deleted and deleted:
            continue
        if not include_hidden and not visible:
            continue
        size_str = _format_size(file_size) if file_size else ""
        size_part = f" size={size_str}" if size_str else ""
        encoded = _enc(item_id)
        items.append(
            (hid, f"HID {hid} (history_dataset_id={encoded}): {name} [dataset, {ext}] state={state}{size_part}")
        )

    for hdca_row in hdca_rows:
        item_id, hid, name, collection_type, deleted, visible = hdca_row
        if not include_deleted and deleted:
            continue
        if not include_hidden and not visible:
            continue
        encoded = _enc(item_id)
        items.append(
            (hid, f"HID {hid} (history_dataset_collection_id={encoded}): {name} [collection, {collection_type}]")
        )

    items.sort(key=lambda x: x[0])
    total = len(items)
    items = items[offset : offset + limit]

    if not items:
        return "No items found in history."

    lines = [f"History items: {len(items)} shown (total={total}, offset={offset}, limit={limit})"]
    lines.extend(line for _, line in items)
    return "\n".join(lines)


async def get_dataset_info(
    session: Session,
    history_id: int,
    hid: int,
    encode_id: Optional[Callable[[int], str]] = None,
) -> str:
    """Get detailed information about a dataset or collection by HID."""
    from galaxy.model import (
        HistoryDatasetAssociation as HDA,
        HistoryDatasetCollectionAssociation as HDCA,
    )

    _enc = encode_id or str

    # Try HDA first
    hda = session.execute(select(HDA).where(HDA.history_id == history_id, HDA.hid == hid)).scalar_one_or_none()

    if hda:
        lines = [
            f"Dataset: {hda.name} (HID {hid}, history_dataset_id={_enc(hda.id)})",
            f"Format: {hda.extension}",
            f"State: {hda.state}",
        ]
        try:
            size = hda.get_size()
            if size:
                lines.append(f"Size: {_format_size(size)}")
        except Exception:
            pass
        create_time = getattr(hda, "create_time", None)
        if create_time:
            lines.append(f"Created: {create_time.isoformat()}")
        if hda.info:
            lines.append(f"Info: {hda.info[:200]}")
        if hda.creating_job:
            job = hda.creating_job
            lines.append(f"Created by tool: {job.tool_id} (v{job.tool_version}), job_id={_enc(job.id)}")
        # Metadata fields
        if hda.metadata and hasattr(hda.metadata, "items"):
            meta_lines = []
            for key, val in list(hda.metadata.items())[:20]:
                val_str = str(val)[:200]
                meta_lines.append(f"  {key}: {val_str}")
            if meta_lines:
                lines.append("Metadata:")
                lines.extend(meta_lines)
        if hda.deleted:
            lines.append("Status: DELETED")
        if not hda.visible:
            lines.append("Status: HIDDEN")
        return "\n".join(lines)

    # Try HDCA
    hdca = session.execute(select(HDCA).where(HDCA.history_id == history_id, HDCA.hid == hid)).scalar_one_or_none()

    if hdca:
        lines = [
            f"Collection: {hdca.name} (HID {hid}, history_dataset_collection_id={_enc(hdca.id)})",
            f"Type: {hdca.collection.collection_type}",
        ]
        if hdca.collection and hdca.collection.elements:
            lines.append(f"Elements: {len(hdca.collection.elements)}")
        if hdca.create_time:
            lines.append(f"Created: {hdca.create_time.isoformat()}")
        if hdca.deleted:
            lines.append("Status: DELETED")
        if not hdca.visible:
            lines.append("Status: HIDDEN")
        return "\n".join(lines)

    return f"No dataset or collection found with HID {hid} in this history."


async def get_dataset_peek(session: Session, history_id: int, hid: int) -> str:
    """Get a preview of a dataset's contents using the pre-computed peek field."""
    from galaxy.model import HistoryDatasetAssociation as HDA

    hda = session.execute(select(HDA).where(HDA.history_id == history_id, HDA.hid == hid)).scalar_one_or_none()

    if not hda:
        return f"No dataset found with HID {hid} in this history."

    if not hda.peek:
        return f"No preview available for {hda.name} (HID {hid}). Format: {hda.extension}."

    # Strip HTML tags from peek (it's stored as HTML for the UI)
    peek_text = re.sub(r"<[^>]+>", "", hda.peek)
    peek_text = peek_text.strip()

    return f"Preview of {hda.name} (HID {hid}, {hda.extension}):\n{peek_text}"


async def get_collection_structure(
    session: Session,
    history_id: int,
    hid: int,
    max_elements: int = 50,
) -> str:
    """Get the structure and element listing of a dataset collection."""
    from galaxy.model import HistoryDatasetCollectionAssociation as HDCA

    hdca = session.execute(select(HDCA).where(HDCA.history_id == history_id, HDCA.hid == hid)).scalar_one_or_none()

    if not hdca:
        return f"No collection found with HID {hid} in this history."

    collection = hdca.collection
    if not collection:
        return f"Collection {hdca.name} (HID {hid}) has no associated dataset collection."

    elements = list(collection.elements) if collection.elements else []
    total = len(elements)

    lines = [
        f"Collection: {hdca.name} (HID {hid})",
        f"Type: {hdca.collection.collection_type}",
        f"Elements: {total}",
    ]

    for elem in elements[:max_elements]:
        if elem.hda:
            lines.append(f"  {elem.element_identifier}: {elem.hda.name} [{elem.hda.extension}] state={elem.hda.state}")
        elif elem.child_collection:
            lines.append(f"  {elem.element_identifier}: [sub-collection, {elem.child_collection.collection_type}]")
        else:
            lines.append(f"  {elem.element_identifier}: (unknown element type)")

    if total > max_elements:
        lines.append(f"  ... and {total - max_elements} more elements")

    return "\n".join(lines)


async def resolve_hid(
    session: Session,
    history_id: int,
    hid: int,
    encode_id: Optional[Callable[[int], str]] = None,
) -> str:
    """Resolve a HID to the directive argument needed for Galaxy markdown.

    Returns the appropriate directive argument string:
    - For datasets: "history_dataset_id=<id>"
    - For collections: "history_dataset_collection_id=<id>"

    Also returns the job_id if a creating job exists (for job directives).
    When encode_id is provided, IDs are encoded for use in API-facing directives.
    """
    from galaxy.model import (
        HistoryDatasetAssociation as HDA,
        HistoryDatasetCollectionAssociation as HDCA,
    )

    _enc = encode_id or str

    hda = session.execute(select(HDA).where(HDA.history_id == history_id, HDA.hid == hid)).scalar_one_or_none()
    if hda:
        lines = [
            f"HID {hid} is a dataset: {hda.name}",
            f"Directive argument: history_dataset_id={_enc(hda.id)}",
        ]
        if hda.creating_job:
            lines.append(f"Creating job: job_id={_enc(hda.creating_job.id)}")
        return "\n".join(lines)

    hdca = session.execute(select(HDCA).where(HDCA.history_id == history_id, HDCA.hid == hid)).scalar_one_or_none()
    if hdca:
        return (
            f"HID {hid} is a collection: {hdca.name}\nDirective argument: history_dataset_collection_id={_enc(hdca.id)}"
        )

    return f"No dataset or collection found with HID {hid} in this history."


def _format_size(size_bytes: Union[int, float, None]) -> str:
    """Format byte size to human-readable string."""
    if size_bytes is None or size_bytes < 0:
        return ""
    size: float = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{size:.1f}PB"
