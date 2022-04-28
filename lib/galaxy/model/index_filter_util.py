"""Utility functions used to adapt galaxy.util.search to Galaxy model index queries."""
from sqlalchemy import (
    and_,
    or_,
)

from galaxy.util.search import FilteredTerm, RawTextTerm


def text_column_filter(column, term: FilteredTerm):
    if term.quoted:
        filter = column == term.text
    else:
        filter = column.ilike(f"%{term.text}%")
    return filter


def raw_text_column_filter(columns: list, term: RawTextTerm):
    like_text = f"%{term.text}%"
    if len(columns) == 1:
        return columns[0].ilike(like_text)
    else:
        return or_(*[c.ilike(like_text) for c in columns])


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
            return assocation_model_class.user_tname.ilike(f"%{term_text}%")
        else:
            return assocation_model_class.user_tname == term_text
