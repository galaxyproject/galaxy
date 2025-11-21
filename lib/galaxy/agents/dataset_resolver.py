"""Utilities for resolving dataset references within Galaxy chats."""

from __future__ import annotations

from typing import Dict, List

import re

from sqlalchemy import and_, select

from galaxy.managers.context import ProvidesUserContext
from galaxy.model import HistoryDatasetAssociation



def _normalize_reference(value: str) -> str:
    value = value or ''
    return re.sub(r'[^0-9A-Za-z_]+', '_', value.strip().lower())

def resolve_dataset_reference(
    trans: ProvidesUserContext,
    user,
    reference: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    """Return datasets owned by the user that match the reference string."""
    if not reference:
        return []

    normalized_reference = _normalize_reference(reference)
    session = trans.sa_session
    like_expression = f"%{reference.lower()}%"

    stmt = (
        select(HistoryDatasetAssociation)
        .where(
            and_(
                HistoryDatasetAssociation.history.has(user_id=user.id),
                HistoryDatasetAssociation.deleted.is_(False),
                HistoryDatasetAssociation.purged.is_(False),
            )
        )
        .limit(limit)
    )

    matches: List[Dict[str, str]] = []
    reference_lower = reference.lower()
    for hda in session.scalars(stmt):
        encoded_id = trans.security.encode_id(hda.id)
        name = hda.name or f"Dataset {hda.hid}"
        normalized_name = _normalize_reference(name)

        candidate_values = [encoded_id, str(hda.hid), name.lower(), normalized_name]
        found = any(candidate and reference_lower in str(candidate).lower() for candidate in candidate_values)
        if not found and normalized_reference and normalized_reference in normalized_name:
            found = True
        if not found:
            continue

        matches.append({"id": encoded_id, "name": name})
    return matches

