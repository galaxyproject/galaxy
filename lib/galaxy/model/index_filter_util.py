"""Utility functions used to adapt galaxy.util.search to Galaxy model index queries."""

from typing import (
    List,
    Union,
)

from sqlalchemy import (
    and_,
    or_,
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


def raw_text_column_filter(columns: List[RawTextSearchableT], term: RawTextTerm):
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
