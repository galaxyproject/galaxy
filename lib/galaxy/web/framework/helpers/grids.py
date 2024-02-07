import logging
import math
from json import (
    dumps,
    loads,
)
from typing import (
    Dict,
    List,
    Optional,
)

from markupsafe import escape
from sqlalchemy.sql.expression import (
    and_,
    false,
    func,
    null,
    or_,
    true,
)

from galaxy.model.item_attrs import (
    get_foreign_key,
    UsesAnnotations,
    UsesItemRatings,
)
from galaxy.util import (
    restore_text,
    sanitize_text,
    string_as_bool,
    unicodify,
)
from galaxy.web.framework import (
    decorators,
    url_for,
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
        link=None,
        attach_popup=False,
        visible=True,
        nowrap=False,
        # Valid values for filterable are ['standard', 'advanced', None]
        filterable=None,
        sortable=True,
        label_id_prefix=None,
        target=None,
        delayed=False,
        escape=True,
    ):
        """Create a grid column."""
        self.label = label
        self.key = key
        self.model_class = model_class
        self.method = method
        self.format = format
        self.link = link
        self.target = target
        self.nowrap = nowrap
        self.attach_popup = attach_popup
        self.visible = visible
        self.filterable = filterable
        self.delayed = delayed
        self.escape = escape
        # Column must have a key to be sortable.
        self.sortable = self.key is not None and sortable
        self.label_id_prefix = label_id_prefix or ""

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

    def get_link(self, trans, grid, item):
        if self.link and self.link(item):
            return self.link(item)
        return None

    def filter(self, trans, user, query, column_filter):
        """Modify query to reflect the column filter."""
        if column_filter == "All":
            pass
        if column_filter == "True":
            query = query.filter_by(**{self.key: True})
        elif column_filter == "False":
            query = query.filter_by(**{self.key: False})
        return query

    def get_accepted_filters(self):
        """Returns a list of accepted filters for this column."""
        accepted_filters_vals = ["False", "True", "All"]
        accepted_filters = []
        for val in accepted_filters_vals:
            args = {self.key: val}
            accepted_filters.append(GridColumnFilter(val, args))
        return accepted_filters

    def sort(self, trans, query, ascending, column_name=None):
        """Sort query using this column."""
        if column_name is None:
            column_name = self.key
        column = getattr(self.model_class, column_name)
        if column is None:
            column = self.model_class.table.c.get(column_name)
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
        query = self.build_initial_query(trans, **kwargs)
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

    # ---- Override these ----------------------------------------------------
    def handle_operation(self, trans, operation, ids, **kwargs):
        pass

    def get_current_item(self, trans, **kwargs):
        return None

    def build_initial_query(self, trans, **kwargs):
        return trans.sa_session.query(self.model_class)
