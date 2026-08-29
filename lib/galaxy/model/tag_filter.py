"""Shared tag-filter predicate, used by both the model layer's paginated
option queries and :mod:`galaxy.managers.taggable`.
"""

from typing import TYPE_CHECKING

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.sql.elements import ColumnElement

if TYPE_CHECKING:
    from sqlalchemy import Table

    from galaxy.model import (
        ItemTagAssociation,
        RepresentById,
    )


def build_tag_filter(
    model_class: "type[RepresentById]",
    tag_association_class: "type[ItemTagAssociation]",
    op: str,
    value: str,
) -> "ColumnElement[bool]":
    """Build the shared ORM predicate for filtering a tagged model.

    A correlated ``EXISTS`` rather than a join predicate: one item can carry
    several tag rows that satisfy ``condition`` at once — ``eq`` on a bare name
    matches both ``gsm`` and ``gsm:v1`` — and a join emits that item once per
    matching row. Callers apply ``LIMIT`` and ``COUNT`` over this predicate, so
    duplicates would silently shorten pages and inflate totals.
    """
    # ``ItemTagAssociation`` is a mixin without ``table``; the concrete
    # subclasses acquire it from the declarative base.
    tag_table: Table = tag_association_class.table  # type: ignore[attr-defined]
    id_column = f"{tag_table.name.rsplit('_tag_association', 1)[0]}_id"
    tag_with_value = tag_association_class.user_tname + ":" + tag_association_class.user_value
    lower_value = value.lower()
    if op == "eq" and ":" not in lower_value:
        # An exact match on a tag with no user_value: concatenating
        # ``user_tname``, ':' and a NULL ``user_value`` would yield NULL.
        condition = func.lower(tag_association_class.user_tname) == lower_value
    elif op == "eq":
        condition = func.lower(tag_with_value) == lower_value
    else:
        condition = func.lower(tag_with_value).contains(lower_value, autoescape=True)
    return (
        select(1)
        .select_from(tag_association_class)
        .where(getattr(tag_association_class, id_column) == model_class.id, condition)
        .correlate_except(tag_association_class)
        .exists()
    )
