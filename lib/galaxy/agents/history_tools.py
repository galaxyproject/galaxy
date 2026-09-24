"""
History data access helpers for the page assistant agent.

Thin string-formatting wrappers over Galaxy managers (HistoryManager,
HistoryContentsManager, HDAManager, DatasetCollectionManager). The
manager layer owns pagination, visibility/deleted filtering, and the
implicit-conversion HID-uniqueness handling so this file does not
re-implement them.
"""

import logging
import re
from functools import partial

import anyio
from sqlalchemy import (
    false,
    sql,
    true,
)

from galaxy.managers import base as manager_base
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.histories import HistoryManager
from galaxy.managers.history_contents import HistoryContentsManager
from galaxy.model import HistoryDatasetAssociation
from galaxy.util import nice_size

log = logging.getLogger(__name__)

_parsed_filter = manager_base.ModelFilterParser.parsed_filter


def _list_history_items_impl(
    trans: ProvidesUserContext,
    history_id: int,
    offset: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    include_hidden: bool = False,
) -> str:
    limit = min(limit, 200)
    history = trans.app[HistoryManager].get_accessible(history_id, trans.user)
    contents_manager = trans.app[HistoryContentsManager]
    filters = []
    if not include_deleted:
        filters.append(_parsed_filter("orm", sql.column("deleted") == false()))
    if not include_hidden:
        filters.append(_parsed_filter("orm", sql.column("visible") == true()))
    items = contents_manager.contents(history, filters=filters, limit=limit, offset=offset)
    total = contents_manager.contents_count(history, filters=filters)
    if not items:
        return "No items found in history."

    encode_id = trans.security.encode_id
    lines = [f"History items: {len(items)} shown (total={total}, offset={offset}, limit={limit})"]
    for item in items:
        lines.append(_format_item_line(item, encode_id))
    return "\n".join(lines)


def _format_item_line(item, encode_id) -> str:
    if isinstance(item, HistoryDatasetAssociation):
        size = item.get_size() if hasattr(item, "get_size") else None
        size_str = _format_size(size)
        size_part = f" size={size_str}" if size_str else ""
        encoded = encode_id(item.id)
        return (
            f"HID {item.hid} (history_dataset_id={encoded}): {item.name} "
            f"[dataset, {item.extension}] state={item.state}{size_part}"
        )
    collection_type = item.collection.collection_type if item.collection else "unknown"
    encoded = encode_id(item.id)
    return f"HID {item.hid} (history_dataset_collection_id={encoded}): {item.name} [collection, {collection_type}]"


async def list_history_items(
    trans: ProvidesUserContext,
    history_id: int,
    offset: int = 0,
    limit: int = 50,
    include_deleted: bool = False,
    include_hidden: bool = False,
) -> str:
    """List datasets and collections in a history, ordered by HID.

    Runs the synchronous manager calls off the event loop.
    """
    return await anyio.to_thread.run_sync(
        partial(
            _list_history_items_impl,
            trans,
            history_id,
            offset=offset,
            limit=limit,
            include_deleted=include_deleted,
            include_hidden=include_hidden,
        )
    )


def _get_dataset_info_impl(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    contents_manager = trans.app[HistoryContentsManager]
    encode_id = trans.security.encode_id

    if hda := contents_manager.get_hda_by_hid(history_id, hid):
        lines = [
            f"Dataset: {hda.name} (HID {hid}, history_dataset_id={encode_id(hda.id)})",
            f"Format: {hda.extension}",
            f"State: {hda.state}",
        ]
        try:
            size = hda.get_size()
            if size:
                lines.append(f"Size: {_format_size(size)}")
        except Exception:
            pass
        if hda.create_time:
            lines.append(f"Created: {hda.create_time.isoformat()}")
        if hda.info:
            lines.append(f"Info: {hda.info[:200]}")
        if hda.creating_job:
            job = hda.creating_job
            lines.append(f"Created by tool: {job.tool_id} (v{job.tool_version}), job_id={encode_id(job.id)}")
        if hda.metadata and hasattr(hda.metadata, "items"):
            meta_lines = [f"  {key}: {str(val)[:200]}" for key, val in list(hda.metadata.items())[:20]]
            if meta_lines:
                lines.append("Metadata:")
                lines.extend(meta_lines)
        if hda.deleted:
            lines.append("Status: DELETED")
        if not hda.visible:
            lines.append("Status: HIDDEN")
        return "\n".join(lines)

    if hdca := contents_manager.get_hdca_by_hid(history_id, hid):
        collection_type = hdca.collection.collection_type if hdca.collection else "unknown"
        lines = [
            f"Collection: {hdca.name} (HID {hid}, history_dataset_collection_id={encode_id(hdca.id)})",
            f"Type: {collection_type}",
        ]
        if hdca.collection and hdca.collection.element_count:
            lines.append(f"Elements: {hdca.collection.element_count}")
        if hdca.create_time:
            lines.append(f"Created: {hdca.create_time.isoformat()}")
        if hdca.deleted:
            lines.append("Status: DELETED")
        if not hdca.visible:
            lines.append("Status: HIDDEN")
        return "\n".join(lines)

    return f"No dataset or collection found with HID {hid} in this history."


async def get_dataset_info(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    """Get detailed information about a dataset or collection by HID."""
    return await anyio.to_thread.run_sync(partial(_get_dataset_info_impl, trans, history_id, hid))


def _get_dataset_peek_impl(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    hda = trans.app[HistoryContentsManager].get_hda_by_hid(history_id, hid)
    if not hda:
        return f"No dataset found with HID {hid} in this history."

    if not hda.peek:
        return f"No preview available for {hda.name} (HID {hid}). Format: {hda.extension}."

    peek_text = re.sub(r"<[^>]+>", "", hda.peek).strip()
    return f"Preview of {hda.name} (HID {hid}, {hda.extension}):\n{peek_text}"


async def get_dataset_peek(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    """Get a preview of a dataset's contents using the pre-computed peek field."""
    return await anyio.to_thread.run_sync(partial(_get_dataset_peek_impl, trans, history_id, hid))


def _get_collection_structure_impl(
    trans: ProvidesUserContext,
    history_id: int,
    hid: int,
    max_elements: int = 50,
) -> str:
    hdca = trans.app[HistoryContentsManager].get_hdca_by_hid(history_id, hid)
    if not hdca:
        return f"No collection found with HID {hid} in this history."

    collection = hdca.collection
    if not collection:
        return f"Collection {hdca.name} (HID {hid}) has no associated dataset collection."

    total = collection.element_count or 0
    page = trans.app[DatasetCollectionManager].get_collection_contents(
        trans, collection.id, limit=max_elements, offset=0
    )

    lines = [
        f"Collection: {hdca.name} (HID {hid})",
        f"Type: {collection.collection_type}",
        f"Elements: {total}",
    ]

    for elem in page:
        if elem.hda:
            lines.append(f"  {elem.element_identifier}: {elem.hda.name} [{elem.hda.extension}] state={elem.hda.state}")
        elif elem.child_collection:
            lines.append(f"  {elem.element_identifier}: [sub-collection, {elem.child_collection.collection_type}]")
        else:
            lines.append(f"  {elem.element_identifier}: (unknown element type)")

    if total > max_elements:
        lines.append(f"  ... and {total - max_elements} more elements")

    return "\n".join(lines)


async def get_collection_structure(
    trans: ProvidesUserContext,
    history_id: int,
    hid: int,
    max_elements: int = 50,
) -> str:
    """Get the structure and element listing of a dataset collection."""
    return await anyio.to_thread.run_sync(
        partial(_get_collection_structure_impl, trans, history_id, hid, max_elements=max_elements)
    )


def _resolve_hid_impl(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    contents_manager = trans.app[HistoryContentsManager]
    encode_id = trans.security.encode_id

    if hda := contents_manager.get_hda_by_hid(history_id, hid):
        lines = [
            f"HID {hid} is a dataset: {hda.name}",
            f"Directive argument: history_dataset_id={encode_id(hda.id)}",
        ]
        if hda.creating_job:
            lines.append(f"Creating job: job_id={encode_id(hda.creating_job.id)}")
        return "\n".join(lines)

    if hdca := contents_manager.get_hdca_by_hid(history_id, hid):
        return (
            f"HID {hid} is a collection: {hdca.name}\n"
            f"Directive argument: history_dataset_collection_id={encode_id(hdca.id)}"
        )

    return f"No dataset or collection found with HID {hid} in this history."


async def resolve_hid(trans: ProvidesUserContext, history_id: int, hid: int) -> str:
    """Resolve a HID to the directive argument needed for Galaxy markdown."""
    return await anyio.to_thread.run_sync(partial(_resolve_hid_impl, trans, history_id, hid))


def _format_size(size_bytes: int | float | None) -> str:
    """Human-readable byte size via galaxy.util.nice_size; "" for missing/negative."""
    if size_bytes is None or size_bytes < 0:
        return ""
    return nice_size(size_bytes)
