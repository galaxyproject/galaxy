import logging
from typing import (
    List,
    Optional,
)

from markupsafe import escape

from galaxy.util import (
    string_as_bool,
    unicodify,
)

log = logging.getLogger(__name__)


class GridColumn:
    def __init__(
        self,
        label,
        key=None,
        model_class=None,
        method=None,
        format=None,
        escape=True,
    ):
        """Create a grid column."""
        self.label = label
        self.key = key
        self.model_class = model_class
        self.method = method
        self.format = format
        self.escape = escape

    def get_value(self, trans, grid, item):
        if self.method:
            value = getattr(grid, self.method)(trans, item)
        elif self.key and hasattr(item, self.key):
            value = getattr(item, self.key)
        else:
            value = None
        if self.format:
            value = self.format(value)
        if self.escape:
            return escape(unicodify(value))
        else:
            return value

    def sort(self, trans, query, ascending, column_name=None):
        """Sort query using this column."""
        if column_name is None:
            column_name = self.key
        column = getattr(self.model_class, column_name)
        if column is None:
            column = self.model_class.__table__.c.get(column_name)
        if ascending:
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc())
        return query


class GridData:
    """
    Specifies the content a grid (data table).
    """

    model_class: Optional[type] = None
    columns: List[GridColumn] = []
    default_limit: int = 1000

    def __init__(self):
        # If a column does not have a model class, set the column's model class
        # to be the grid's model class.
        for column in self.columns:
            if not column.model_class:
                column.model_class = self.model_class

    def __call__(self, trans, **kwargs):
        limit = kwargs.get("limit", self.default_limit)
        offset = kwargs.get("offset", 0)

        # Build initial query
        query = trans.sa_session.query(self.model_class)
        query = self.apply_query_filter(query, **kwargs)

        # Process sort arguments.
        sort_by = kwargs.get("sort_by", self.default_sort_key)
        sort_desc = string_as_bool(kwargs.get("sort_desc", True))
        for column in self.columns:
            if column.key == sort_by:
                query = column.sort(trans, query, not sort_desc, column_name=sort_by)
                break

        # Process limit and offset.
        rows_total = query.count()
        query = query.limit(limit).offset(offset)

        # Populate and return response
        grid_config = {
            "rows": [],
            "rows_total": rows_total,
        }
        for row in query:
            row_dict = {
                "id": trans.security.encode_id(row.id),
            }
            for column in self.columns:
                value = column.get_value(trans, self, row)
                row_dict[column.key] = value
            grid_config["rows"].append(row_dict)
        return grid_config
