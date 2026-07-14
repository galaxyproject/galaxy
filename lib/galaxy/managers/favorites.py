"""Manager for a user's favorites: tools, curated tool tags, and EDAM
operations/topics, plus the user-visible ordering across all of them.

The favorites payload is persisted as a JSON document inside
``user.preferences["favorites"]`` (a Text column). This manager owns its
schema — validation, deduplication, and the ``order`` invariant that
mirrors the per-type lists — so that controllers stay thin and other
call sites can reuse the same logic without going through HTTP.
"""

import json
from typing import Any

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import User
from galaxy.schema.schema import (
    FavoriteObjectType,
    FavoriteOrderPayload,
)

FAVORITE_OBJECT_TYPE_VALUES = tuple(object_type.value for object_type in FavoriteObjectType)


class FavoritesManager:
    """Load, mutate, and persist a user's favorites payload."""

    def get(self, user: User) -> dict[str, Any]:
        """Return the user's favorites normalized to the canonical shape."""
        raw = json.loads(user.preferences["favorites"]) if "favorites" in user.preferences else {}
        return _normalize(raw)

    def add(
        self,
        trans: ProvidesUserContext,
        user: User,
        object_type: FavoriteObjectType,
        raw_object_id: str,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        favorites = self.get(user)
        canonical_id = self._resolve_object_id(trans, user, object_type, raw_object_id)
        if canonical_id not in (favorite_list := favorites[object_type.value]):
            favorite_list.append(canonical_id)
            favorites = self._save(trans, user, favorites, commit=commit)
        return favorites

    def remove(
        self,
        trans: ProvidesUserContext,
        user: User,
        object_type: FavoriteObjectType,
        object_id: str,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        favorites = self.get(user)
        favorite_list = favorites[object_type.value]
        if object_id not in favorite_list:
            raise exceptions.ObjectNotFound("Given object is not in the list of favorites")
        favorite_list.remove(object_id)
        return self._save(trans, user, favorites, commit=commit)

    def set_order(
        self,
        trans: ProvidesUserContext,
        user: User,
        payload: FavoriteOrderPayload,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        favorites = self.get(user)
        # `FavoriteOrderItem` inherits from `Model`, which sets
        # `use_enum_values=True`; `item.object_type` is already a plain string.
        requested_order = [_order_entry(item.object_type, item.object_id) for item in payload.order]
        expected_keys = {(entry["object_type"], entry["object_id"]) for entry in favorites["order"]}
        requested_keys = {(entry["object_type"], entry["object_id"]) for entry in requested_order}
        if len(requested_order) != len(favorites["order"]) or requested_keys != expected_keys:
            raise exceptions.RequestParameterInvalidException(
                "Favorite order must contain every current favorite exactly once."
            )
        favorites["order"] = requested_order
        for object_type in FAVORITE_OBJECT_TYPE_VALUES:
            favorites[object_type] = [
                entry["object_id"] for entry in requested_order if entry["object_type"] == object_type
            ]
        return self._save(trans, user, favorites, commit=commit)

    def _save(
        self,
        trans: ProvidesUserContext,
        user: User,
        favorites: dict[str, Any],
        *,
        commit: bool,
    ) -> dict[str, Any]:
        user.preferences["favorites"] = json.dumps(favorites)
        if commit:
            trans.sa_session.commit()
        return favorites

    def _resolve_object_id(
        self,
        trans: ProvidesUserContext,
        user: User,
        object_type: FavoriteObjectType,
        raw_object_id: str,
    ) -> str:
        if object_type is FavoriteObjectType.tools:
            return _resolve_tool_id(trans, user, raw_object_id)
        if object_type is FavoriteObjectType.tags:
            return _resolve_against_set(
                raw_object_id,
                trans.app.toolbox.curated_tool_tags,
                "Favorite tag cannot be empty.",
                "Could not find a curated tool tag named '{object_id}'.",
            )
        if object_type is FavoriteObjectType.edam_operations:
            return _resolve_against_set(
                raw_object_id,
                trans.app.toolbox.tool_edam_operations,
                "Favorite EDAM operation cannot be empty.",
                "Could not find an EDAM operation named '{object_id}'.",
            )
        if object_type is FavoriteObjectType.edam_topics:
            return _resolve_against_set(
                raw_object_id,
                trans.app.toolbox.tool_edam_topics,
                "Favorite EDAM topic cannot be empty.",
                "Could not find an EDAM topic named '{object_id}'.",
            )
        # FavoriteObjectType is exhaustive; FastAPI rejects unknown values upstream.
        raise exceptions.RequestParameterInvalidException(f"Unsupported favorite object type '{object_type}'.")


def _resolve_tool_id(trans: ProvidesUserContext, user: User, raw_object_id: str) -> str:
    tool = trans.app.toolbox.get_tool(raw_object_id)
    if not tool:
        raise exceptions.ObjectNotFound(f"Could not find tool with id '{raw_object_id}'.")
    if not tool.allow_user_access(user):
        raise exceptions.AuthenticationFailed(f"Access denied for tool with id '{raw_object_id}'.")
    # Persist the canonical `tool.id` (which `get_tool` returns after
    # resolving aliases, old_ids, and versioned ids) so the client — which
    # keys `toolStore.toolsById` by the canonical id — can always render
    # the favorite. Without this, an alias like `cat1/1.0.0` would be
    # stored verbatim and then silently dropped from the My Tools panel.
    assert tool.id is not None
    return tool.id


def _resolve_against_set(
    raw_object_id: str,
    valid_ids: frozenset[str],
    empty_message: str,
    not_found_template: str,
) -> str:
    object_id = raw_object_id.strip()
    if not object_id:
        raise exceptions.RequestParameterInvalidException(empty_message)
    if object_id not in valid_ids:
        raise exceptions.ObjectNotFound(not_found_template.format(object_id=object_id))
    return object_id


def _order_entry(object_type: str, object_id: str) -> dict[str, str]:
    return {"object_type": object_type, "object_id": object_id}


def _normalize(favorites: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for object_type in FAVORITE_OBJECT_TYPE_VALUES:
        object_ids = favorites.get(object_type) or []
        seen_ids: set[str] = set()
        deduped: list[str] = []
        for object_id in object_ids:
            if isinstance(object_id, str) and object_id and object_id not in seen_ids:
                seen_ids.add(object_id)
                deduped.append(object_id)
        normalized[object_type] = deduped

    seen_entries: set[tuple[str, str]] = set()
    order: list[dict[str, str]] = []
    for raw_entry in favorites.get("order") or []:
        if not isinstance(raw_entry, dict):
            continue
        raw_object_type = raw_entry.get("object_type")
        raw_object_id = raw_entry.get("object_id")
        if not isinstance(raw_object_type, str) or not isinstance(raw_object_id, str):
            continue
        entry_key = (raw_object_type, raw_object_id)
        if (
            raw_object_type in FAVORITE_OBJECT_TYPE_VALUES
            and raw_object_id in normalized[raw_object_type]
            and entry_key not in seen_entries
        ):
            seen_entries.add(entry_key)
            order.append(_order_entry(raw_object_type, raw_object_id))

    for object_type in FAVORITE_OBJECT_TYPE_VALUES:
        for object_id in normalized[object_type]:
            entry_key = (object_type, object_id)
            if entry_key not in seen_entries:
                seen_entries.add(entry_key)
                order.append(_order_entry(object_type, object_id))

    normalized["order"] = order
    return normalized
