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


class ReverseSortColumn(GridColumn):
    """Column that reverses sorting; this is useful when the natural sort is descending."""

    def sort(self, trans, query, ascending, column_name=None):
        return GridColumn.sort(self, trans, query, (not ascending), column_name=column_name)


class TextColumn(GridColumn):
    """Generic column that employs freetext and, hence, supports freetext, case-independent filtering."""

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter using free text, case independence."""
        if column_filter == "All":
            pass
        elif column_filter:
            query = query.filter(self.get_filter(trans, user, column_filter))
        return query

    def get_filter(self, trans, user, column_filter):
        """Returns a SQLAlchemy criterion derived from column_filter."""
        if isinstance(column_filter, str):
            return self.get_single_filter(user, column_filter)
        elif isinstance(column_filter, list):
            clause_list = []
            for filter in column_filter:
                clause_list.append(self.get_single_filter(user, filter))
            return and_(*clause_list)

    def get_single_filter(self, user, a_filter):
        """
        Returns a SQLAlchemy criterion derived for a single filter. Single filter
        is the most basic filter--usually a string--and cannot be a list.
        """
        # Queries that include table joins cannot guarantee that table column names will be
        # unique, so check to see if a_filter is of type <TableName>.<ColumnName>.
        if self.key.find(".") > -1:
            a_key = self.key.split(".")[1]
        else:
            a_key = self.key
        model_class_key_field = getattr(self.model_class, a_key)
        return func.lower(model_class_key_field).like(f"%{a_filter.lower()}%")

    def sort(self, trans, query, ascending, column_name=None):
        """Sort column using case-insensitive alphabetical sorting."""
        if column_name is None:
            column_name = self.key
        if ascending:
            query = query.order_by(func.lower(self.model_class.table.c.get(column_name)).asc())
        else:
            query = query.order_by(func.lower(self.model_class.table.c.get(column_name)).desc())
        return query


class DateTimeColumn(TextColumn):
    def sort(self, trans, query, ascending, column_name=None):
        """Sort query using this column."""
        return GridColumn.sort(self, trans, query, ascending, column_name=column_name)


class BooleanColumn(TextColumn):
    def sort(self, trans, query, ascending, column_name=None):
        """Sort query using this column."""
        return GridColumn.sort(self, trans, query, ascending, column_name=column_name)

    def get_single_filter(self, user, a_filter):
        if self.key.find(".") > -1:
            a_key = self.key.split(".")[1]
        else:
            a_key = self.key
        model_class_key_field = getattr(self.model_class, a_key)
        return model_class_key_field == a_filter


class IntegerColumn(TextColumn):
    """
    Integer column that employs freetext, but checks that the text is an integer,
    so support filtering on integer values.

    IMPORTANT NOTE: grids that use this column type should not include the column
    in the cols_to_filter list of MulticolFilterColumn ( i.e., searching on this
    column type should not be performed in the grid's standard search - it won't
    throw exceptions, but it also will not find what you're looking for ).  Grids
    that search on this column should use 'filterable="advanced"' so that searching
    is only performed in the advanced search component, restricting the search to
    the specific column.

    This is useful for searching on object ids or other integer columns.  See the
    JobIdColumn column in the SpecifiedDateListGrid class in the jobs controller of
    the reports webapp for an example.
    """

    def get_single_filter(self, user, a_filter):
        model_class_key_field = getattr(self.model_class, self.key)
        assert int(a_filter), "The search entry must be an integer"
        return model_class_key_field == int(a_filter)

    def sort(self, trans, query, ascending, column_name=None):
        """Sort query using this column."""
        return GridColumn.sort(self, trans, query, ascending, column_name=column_name)


class CommunityRatingColumn(GridColumn, UsesItemRatings):
    """Column that displays community ratings for an item."""

    def get_value(self, trans, grid, item):
        if not hasattr(item, "average_rating"):
            # No prefetched column property, generate it on the fly.
            ave_item_rating, num_ratings = self.get_ave_item_rating_data(
                trans.sa_session, item, webapp_model=trans.model
            )
        else:
            ave_item_rating = item.average_rating
            num_ratings = 2  # just used for pluralization
        if not ave_item_rating:
            ave_item_rating = 0
        return trans.fill_template(
            "tool_shed_rating.mako",
            ave_item_rating=ave_item_rating,
            num_ratings=num_ratings,
            item_id=trans.security.encode_id(item.id),
        )

    def sort(self, trans, query, ascending, column_name=None):
        # Get the columns that connect item's table and item's rating association table.
        item_rating_assoc_class = getattr(trans.model, f"{self.model_class.__name__}RatingAssociation")
        foreign_key = get_foreign_key(item_rating_assoc_class, self.model_class)
        fk_col = foreign_key.parent
        referent_col = foreign_key.get_referent(self.model_class.table)
        # Do sorting using a subquery.
        # Subquery to get average rating for each item.
        ave_rating_subquery = (
            trans.sa_session.query(fk_col, func.avg(item_rating_assoc_class.table.c.rating).label("avg_rating"))
            .group_by(fk_col)
            .subquery()
        )
        # Integrate subquery into main query.
        query = query.outerjoin((ave_rating_subquery, referent_col == ave_rating_subquery.columns[fk_col.name]))
        # Sort using subquery results; use coalesce to avoid null values.
        if (
            not ascending
        ):  # TODO: for now, reverse sorting b/c first sort is ascending, and that should be the natural sort.
            query = query.order_by(func.coalesce(ave_rating_subquery.c.avg_rating, 0).asc())
        else:
            query = query.order_by(func.coalesce(ave_rating_subquery.c.avg_rating, 0).desc())
        return query


class OwnerAnnotationColumn(TextColumn, UsesAnnotations):
    """Column that displays and filters item owner's annotations."""

    def __init__(self, col_name, key, model_class=None, model_annotation_association_class=None, filterable=None):
        GridColumn.__init__(self, col_name, key=key, model_class=model_class, filterable=filterable)
        self.sortable = False
        self.model_annotation_association_class = model_annotation_association_class

    def get_value(self, trans, grid, item):
        """Returns first 150 characters of annotation."""
        annotation = self.get_item_annotation_str(trans.sa_session, item.user, item)
        if annotation:
            ann_snippet = annotation[:155]
            if len(annotation) > 155:
                ann_snippet = ann_snippet[: ann_snippet.rfind(" ")]
                ann_snippet += "..."
        else:
            ann_snippet = ""
        return escape(ann_snippet)

    def get_single_filter(self, user, a_filter):
        """Filter by annotation and annotation owner."""
        return self.model_class.annotations.any(
            and_(
                func.lower(self.model_annotation_association_class.annotation).like(f"%{a_filter.lower()}%"),
                # TODO: not sure why, to filter by owner's annotations, we have to do this rather than
                # 'self.model_class.user==self.model_annotation_association_class.user'
                self.model_annotation_association_class.table.c.user_id == self.model_class.table.c.user_id,
            )
        )


class CommunityTagsColumn(TextColumn):
    """Column that supports community tags."""

    def __init__(
        self, col_name, key, model_class=None, model_tag_association_class=None, filterable=None, grid_name=None
    ):
        GridColumn.__init__(
            self, col_name, key=key, model_class=model_class, nowrap=True, filterable=filterable, sortable=False
        )
        self.model_tag_association_class = model_tag_association_class
        # Column-specific attributes.
        self.grid_name = grid_name

    def get_value(self, trans, grid, item):
        return trans.fill_template(
            "/tagging_common.mako",
            tag_type="community",
            trans=trans,
            user=trans.get_user(),
            tagged_item=item,
            elt_context=self.grid_name,
            tag_click_fn="add_tag_to_grid_filter",
            use_toggle_link=True,
        )

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter model_class by tag. Multiple filters are ANDed."""
        if column_filter == "All":
            pass
        elif column_filter:
            query = query.filter(self.get_filter(trans, user, column_filter))
        return query

    def get_filter(self, trans, user, column_filter):
        # Parse filter to extract multiple tags.
        if isinstance(column_filter, list):
            # Collapse list of tags into a single string; this is redundant but effective. TODO: fix this by iterating over tags.
            column_filter = ",".join(column_filter)
        raw_tags = trans.app.tag_handler.parse_tags(column_filter)
        clause_list = []
        for name, value in raw_tags:
            if name:
                # Filter by all tags.
                clause_list.append(
                    self.model_class.tags.any(
                        func.lower(self.model_tag_association_class.user_tname).like(f"%{name.lower()}%")
                    )
                )
                if value:
                    # Filter by all values.
                    clause_list.append(
                        self.model_class.tags.any(
                            func.lower(self.model_tag_association_class.user_value).like(f"%{value.lower()}%")
                        )
                    )
        return and_(*clause_list)


class IndividualTagsColumn(CommunityTagsColumn):
    """Column that supports individual tags."""

    def get_value(self, trans, grid, item):
        return trans.fill_template(
            "/tagging_common.mako",
            tag_type="individual",
            user=trans.user,
            tagged_item=item,
            elt_context=self.grid_name,
            tag_click_fn="add_tag_to_grid_filter",
            use_toggle_link=True,
        )

    def get_filter(self, trans, user, column_filter):
        # Parse filter to extract multiple tags.
        if isinstance(column_filter, list):
            # Collapse list of tags into a single string; this is redundant but effective. TODO: fix this by iterating over tags.
            column_filter = ",".join(column_filter)
        raw_tags = trans.app.tag_handler.parse_tags(column_filter)
        clause_list = []
        for name, value in raw_tags:
            if name:
                # Filter by individual's tag names.
                clause_list.append(
                    self.model_class.tags.any(
                        and_(
                            func.lower(self.model_tag_association_class.user_tname).like(f"%{name.lower()}%"),
                            self.model_tag_association_class.user == user,
                        )
                    )
                )
                if value:
                    # Filter by individual's tag values.
                    clause_list.append(
                        self.model_class.tags.any(
                            and_(
                                func.lower(self.model_tag_association_class.user_value).like(f"%{value.lower()}%"),
                                self.model_tag_association_class.user == user,
                            )
                        )
                    )
        return and_(*clause_list)


class MulticolFilterColumn(TextColumn):
    """Column that performs multicolumn filtering."""

    def __init__(self, col_name, cols_to_filter, key, visible, filterable="default"):
        GridColumn.__init__(self, col_name, key=key, visible=visible, filterable=filterable)
        self.cols_to_filter = cols_to_filter

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter model_class by tag. Multiple filters are ANDed."""
        if column_filter == "All":
            return query
        if isinstance(column_filter, list):
            clause_list = []
            for filter in column_filter:
                part_clause_list = []
                for column in self.cols_to_filter:
                    part_clause_list.append(column.get_filter(trans, user, filter))
                clause_list.append(or_(*part_clause_list))
            complete_filter = and_(*clause_list)
        else:
            clause_list = []
            for column in self.cols_to_filter:
                clause_list.append(column.get_filter(trans, user, column_filter))
            complete_filter = or_(*clause_list)
        return query.filter(complete_filter)


class OwnerColumn(TextColumn):
    """Column that lists item's owner."""

    def get_value(self, trans, grid, item):
        return item.user.username

    def sort(self, trans, query, ascending, column_name=None):
        """Sort column using case-insensitive alphabetical sorting on item's username."""
        if ascending:
            query = query.order_by(func.lower(self.model_class.username).asc())
        else:
            query = query.order_by(func.lower(self.model_class.username).desc())
        return query


class PublicURLColumn(TextColumn):
    """Column displays item's public URL based on username and slug."""

    def get_link(self, trans, grid, item):
        if item.user.username and item.slug:
            return dict(action="display_by_username_and_slug", username=item.user.username, slug=item.slug)
        elif not item.user.username:
            # TODO: provide link to set username.
            return None
        elif not item.user.slug:
            # TODO: provide link to set slug.
            return None


class DeletedColumn(GridColumn):
    """Column that tracks and filters for items with deleted attribute."""

    def get_accepted_filters(self):
        """Returns a list of accepted filters for this column."""
        accepted_filter_labels_and_vals = {"active": "False", "deleted": "True", "all": "All"}
        accepted_filters = []
        for label, val in accepted_filter_labels_and_vals.items():
            args = {self.key: val}
            accepted_filters.append(GridColumnFilter(label, args))
        return accepted_filters

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter self.model_class by state."""
        if column_filter == "All":
            pass
        elif column_filter in ["True", "False"]:
            query = query.filter(self.model_class.deleted == (column_filter == "True"))
        return query


class PurgedColumn(GridColumn):
    """Column that tracks and filters for items with purged attribute."""

    def get_accepted_filters(self):
        """Returns a list of accepted filters for this column."""
        accepted_filter_labels_and_vals = {"nonpurged": "False", "purged": "True", "all": "All"}
        accepted_filters = []
        for label, val in accepted_filter_labels_and_vals.items():
            args = {self.key: val}
            accepted_filters.append(GridColumnFilter(label, args))
        return accepted_filters

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter self.model_class by state."""
        if column_filter == "All":
            pass
        elif column_filter in ["True", "False"]:
            query = query.filter(self.model_class.purged == (column_filter == "True"))
        return query


class StateColumn(GridColumn):
    """
    Column that tracks and filters for items with state attribute.

    IMPORTANT NOTE: self.model_class must have a states Bunch or dict if
    this column type is used in the grid.
    """

    def get_value(self, trans, grid, item):
        return item.state

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter self.model_class by state."""
        if column_filter == "All":
            pass
        elif column_filter in [v for k, v in self.model_class.states.items()]:
            query = query.filter(self.model_class.state == column_filter)
        return query

    def get_accepted_filters(self):
        """Returns a list of accepted filters for this column."""
        all = GridColumnFilter("all", {self.key: "All"})
        accepted_filters = [all]
        for v in self.model_class.states.values():
            args = {self.key: v}
            accepted_filters.append(GridColumnFilter(v, args))
        return accepted_filters


class SharingStatusColumn(GridColumn):
    """Grid column to indicate sharing status."""

    def __init__(self, *args, **kwargs):
        self.use_shared_with_count = kwargs.pop("use_shared_with_count", False)
        super().__init__(*args, **kwargs)

    def get_value(self, trans, grid, item):
        # Delete items cannot be shared.
        if item.deleted:
            return ""
        # Build a list of sharing for this item.
        sharing_statuses = []
        if self._is_shared(item):
            sharing_statuses.append("Shared")
        if item.importable:
            sharing_statuses.append("Accessible")
        if item.published:
            sharing_statuses.append("Published")
        return ", ".join(sharing_statuses)

    def _is_shared(self, item):
        if self.use_shared_with_count:
            # optimization to skip join for users_shared_with and loading in that data.
            return item.users_shared_with_count > 0

        return item.users_shared_with

    def filter(self, trans, user, query, column_filter):
        """Modify query to filter histories by sharing status."""
        if column_filter == "All":
            pass
        elif column_filter:
            if column_filter == "private":
                query = query.filter(self.model_class.users_shared_with == null())
                query = query.filter(self.model_class.importable == false())
            elif column_filter == "shared":
                query = query.filter(self.model_class.users_shared_with != null())
            elif column_filter == "accessible":
                query = query.filter(self.model_class.importable == true())
            elif column_filter == "published":
                query = query.filter(self.model_class.published == true())
        return query

    def get_accepted_filters(self):
        """Returns a list of accepted filters for this column."""
        accepted_filter_labels_and_vals = {}
        accepted_filter_labels_and_vals["private"] = "private"
        accepted_filter_labels_and_vals["shared"] = "shared"
        accepted_filter_labels_and_vals["accessible"] = "accessible"
        accepted_filter_labels_and_vals["published"] = "published"
        accepted_filter_labels_and_vals["all"] = "All"
        accepted_filters = []
        for label, val in accepted_filter_labels_and_vals.items():
            args = {self.key: val}
            accepted_filters.append(GridColumnFilter(label, args))
        return accepted_filters


class GridOperation:
    def __init__(
        self,
        label,
        key=None,
        condition=None,
        allow_multiple=True,
        allow_popup=True,
        target=None,
        url_args=None,
        async_compatible=False,
        confirm=None,
        global_operation=None,
    ):
        self.label = label
        self.key = key
        self.allow_multiple = allow_multiple
        self.allow_popup = allow_popup
        self.condition = condition
        self.target = target
        self.url_args = url_args
        self.async_compatible = async_compatible
        # if 'confirm' is set, then ask before completing the operation
        self.confirm = confirm
        # specify a general operation that acts on the full grid
        # this should be a function returning a dictionary with parameters
        # to pass to the URL, similar to GridColumn links:
        # global_operation=(lambda: dict(operation="download")
        self.global_operation = global_operation

    def get_url_args(self, item):
        if self.url_args:
            if callable(self.url_args):
                url_args = self.url_args(item)
            else:
                url_args = dict(self.url_args)
            url_args["id"] = item.id
            return url_args
        else:
            return dict(operation=self.label, id=item.id)

    def allowed(self, item):
        if self.condition:
            return bool(self.condition(item))
        else:
            return True


class DisplayByUsernameAndSlugGridOperation(GridOperation):
    """Operation to display an item by username and slug."""

    def get_url_args(self, item):
        return {"action": "display_by_username_and_slug", "username": item.user.username, "slug": item.slug}


class GridAction:
    def __init__(self, label=None, url_args=None, target=None):
        self.label = label
        self.url_args = url_args
        self.target = target


class GridColumnFilter:
    def __init__(self, label, args=None):
        self.label = label
        self.args = args

    def get_url_args(self):
        rval = {}
        for k, v in self.args.items():
            rval[f"f-{k}"] = v
        return rval


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
