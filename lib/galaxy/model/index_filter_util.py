"""Utility functions used to adapt galaxy.util.search to Galaxy model index queries."""

from typing import (
    Union,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.orm import (
    aliased,
    InstrumentedAttribute,
)
from sqlalchemy.sql.expression import BinaryExpression

from galaxy import model
from galaxy.util.search import (
    FilteredTerm,
    RawTextTerm,
)


def text_column_filter(column, term: FilteredTerm):
    if term.quoted:
        filter = column == term.text
    else:
        filter = column.ilike(f"%{term.text}%")
    return filter


RawTextSearchableT = Union[BinaryExpression, InstrumentedAttribute]


def raw_text_column_filter(columns: list[RawTextSearchableT], term: RawTextTerm):
    like_text = f"%{term.text}%"
    return or_(*[c.ilike(like_text) if isinstance(c, InstrumentedAttribute) else c for c in columns])


def tag_filter(assocation_model_class, term_text, quoted: bool = False):
    if ":" in term_text:
        key, value = term_text.rsplit(":", 1)
        if not quoted:
            return and_(
                assocation_model_class.user_tname.ilike(key),
                assocation_model_class.user_value.ilike(f"%{value}%"),
            )
        else:
            return and_(
                assocation_model_class.user_tname == key,
                assocation_model_class.user_value == value,
            )
    else:
        if not quoted:
            return or_(
                assocation_model_class.user_tname.ilike(f"%{term_text}%"),
                and_(
                    assocation_model_class.user_tname.ilike("name"),
                    assocation_model_class.user_value.ilike(f"%{term_text}%"),
                ),
            )
        else:
            return assocation_model_class.user_tname == term_text


def append_user_filter(query, model_class, term: FilteredTerm):
    alias = aliased(model.User)
    query = query.outerjoin(model_class.user.of_type(alias))
    query = query.filter(text_column_filter(alias.username, term))
    return query


def tag_exists_filter(association_model_class, fk_column, parent_id_column, term_text, quoted: bool = False):
    """Correlated EXISTS subquery that matches any tag on the parent row against term_text.

    Prefer this over adding a per-term outer join on the tag-association table: each
    extra outer join multiplies rows (forcing an expensive DISTINCT) and in free-text
    search N whitespace-separated terms produce N such joins.
    """
    return (
        select(1)
        .select_from(association_model_class)
        .where(fk_column == parent_id_column)
        .where(tag_filter(association_model_class, term_text, quoted))
        .correlate_except(association_model_class)
        .exists()
    )


def user_exists_filter(owner_id_column, term_text: str):
    """Correlated EXISTS subquery that matches the owning user's username."""
    return (
        select(1)
        .select_from(model.User)
        .where(model.User.id == owner_id_column)
        .where(model.User.username.ilike(f"%{term_text}%"))
        .correlate_except(model.User)
        .exists()
    )
