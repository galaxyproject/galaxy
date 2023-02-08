"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""
import json
import logging
from typing import (
    Any,
    Dict,
    List,
)

from sqlalchemy import (
    asc,
    cast,
    desc,
    false,
    func,
    Integer,
    literal,
    nullsfirst,
    nullslast,
    select,
    sql,
    true,
)
from sqlalchemy.orm import (
    joinedload,
    undefer,
)

from galaxy import (
    exceptions as glx_exceptions,
    model,
)
from galaxy.managers import (
    annotatable,
    base,
    deletable,
    genomes,
    hdas,
    hdcas,
    taggable,
    tools,
)
from galaxy.managers.job_connections import JobConnectionsManager
from galaxy.schema import ValueFilterQueryParams
from galaxy.structured_app import MinimalManagerApp
from .base import (
    parse_bool,
    raise_filter_err,
    Serializer,
)

log = logging.getLogger(__name__)


# into its own class to have it's own filters, etc.
# TODO: but can't inherit from model manager (which assumes only one model)
class HistoryContentsManager(base.SortableManager):
    root_container_class = model.History

    contained_class = model.HistoryDatasetAssociation
    contained_class_manager_class = hdas.HDAManager
    contained_class_type_name = "dataset"

    subcontainer_class = model.HistoryDatasetCollectionAssociation
    subcontainer_class_manager_class = hdcas.HDCAManager
    subcontainer_class_type_name = "dataset_collection"

    #: the columns which are common to both subcontainers and non-subcontainers.
    #  (Also the attributes that may be filtered or orderered_by)
    common_columns = (
        "history_id",
        "history_content_type",
        "id",
        "type_id",
        "hid",
        # joining columns
        "extension",
        "dataset_id",
        "collection_id",
        "name",
        "state",
        "size",
        "deleted",
        "purged",
        "visible",
        "create_time",
        "update_time",
    )
    default_order_by = "hid"

    def __init__(self, app: MinimalManagerApp):
        self.app = app
        self.contained_manager = app[self.contained_class_manager_class]
        self.subcontainer_manager = app[self.subcontainer_class_manager_class]

    # ---- interface
    def contained(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns non-subcontainer objects within `container`.
        """
        filter_to_inside_container = self._get_filter_for_contained(container, self.contained_class)
        filters = base.munge_lists(filter_to_inside_container, filters)
        return self.contained_manager.list(filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs)

    def subcontainers(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns only the containers within `container`.
        """
        filter_to_inside_container = self._get_filter_for_contained(container, self.subcontainer_class)
        filters = base.munge_lists(filter_to_inside_container, filters)
        # TODO: collections.DatasetCollectionManager doesn't have the list
        # return self.subcontainer_manager.list( filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs )
        return self._session().query(self.subcontainer_class).filter(filters).all()

    def contents(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns a list of both/all types of contents, filtered and in some order.
        """
        # TODO?: we could branch here based on 'if limit is None and offset is None' - to a simpler (non-union) query
        # for now, I'm just using this (even for non-limited/offset queries) to reduce code paths
        return self._union_of_contents(
            container, filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs
        )

    def contents_count(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns a count of both/all types of contents, based on the given filters.
        """
        return self.contents_query(
            container, filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs
        ).count()

    def contents_query(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns the contents union query for subqueries, etc.
        """
        return self._union_of_contents_query(
            container, filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs
        )

    # order_by parsing - similar to FilterParser but not enough yet to warrant a class?
    def parse_order_by(self, order_by_string, default=None):
        """Return an ORM compatible order_by using the given string"""
        available = ["create_time", "extension", "hid", "history_id", "name", "update_time", "size"]
        for attribute in available:
            attribute_dsc = f"{attribute}-dsc"
            attribute_asc = f"{attribute}-asc"
            if order_by_string in (attribute, attribute_dsc):
                order_by = desc(attribute)
                if attribute == "size":
                    return nullslast(order_by)
                return order_by
            if order_by_string == attribute_asc:
                order_by = asc(attribute)
                if attribute == "size":
                    return nullsfirst(order_by)
                return order_by

        if default:
            return self.parse_order_by(default)
        raise glx_exceptions.RequestParameterInvalidException(
            "Unknown order_by", order_by=order_by_string, available=available
        )

    # history specific methods
    def state_counts(self, history):
        """
        Return a dictionary containing the counts of all contents in each state
        keyed by the distinct states.

        Note: does not include deleted/hidden contents.
        """
        filters = [
            base.ModelFilterParser.parsed_filter("orm", sql.column("deleted") == false()),
            base.ModelFilterParser.parsed_filter("orm", sql.column("visible") == true()),
        ]
        contents_subquery = self._union_of_contents_query(history, filters=filters).subquery()
        statement = (
            sql.select([sql.column("state"), func.count("*")])
            .select_from(contents_subquery)
            .group_by(sql.column("state"))
        )
        counts = self.app.model.context.execute(statement).fetchall()
        return dict(counts)

    def active_counts(self, history):
        """
        Return a dictionary keyed with 'deleted', 'hidden', and 'active' with values
        for each representing the count of contents in each state.

        Note: counts for deleted and hidden overlap; In other words, a dataset that's
        both deleted and hidden will be added to both totals.
        """
        hda_select = self._active_counts_statement(model.HistoryDatasetAssociation, history.id)
        hdca_select = self._active_counts_statement(model.HistoryDatasetCollectionAssociation, history.id)
        subquery = hda_select.union_all(hdca_select).subquery()
        statement = select(
            cast(func.sum(subquery.c.deleted), Integer).label("deleted"),
            cast(func.sum(subquery.c.hidden), Integer).label("hidden"),
            cast(func.sum(subquery.c.active), Integer).label("active"),
        )
        returned = self.app.model.context.execute(statement).one()
        return dict(returned)

    def _active_counts_statement(self, model_class, history_id):
        deleted_attr = model_class.deleted
        visible_attr = model_class.visible
        table_attr = model_class.table
        return (
            select(
                func.sum(cast(deleted_attr, Integer)).label("deleted"),
                func.sum(cast(visible_attr == false(), Integer)).label("hidden"),
                func.sum(func.abs(cast(visible_attr, Integer) * (cast(deleted_attr, Integer) - 1))).label("active"),
            )
            .select_from(table_attr)
            .filter_by(history_id=history_id)
        )

    def map_datasets(self, history, fn, **kwargs):
        """
        Iterate over the datasets of a given history, recursing into collections, and
        calling fn on each dataset.

        Uses the same kwargs as `contents` above.
        """
        returned = []
        contents = self.contents(history, **kwargs)
        for content in contents:
            if isinstance(content, self.subcontainer_class):
                processed_list = self.subcontainer_manager.map_datasets(content, fn)
                returned.extend(processed_list)
            else:
                processed = fn(content)
                returned.append(processed)
        return returned

    # ---- private
    def _session(self):
        return self.app.model.context

    def _filter_to_contents_query(self, container, content_class, **kwargs):
        # TODO: use list (or by_history etc.)
        container_filter = self._get_filter_for_contained(container, content_class)
        query = self._session().query(content_class).filter(container_filter)
        return query

    def _get_filter_for_contained(self, container, content_class):
        return content_class.history == container

    def _union_of_contents(self, container, expand_models=True, **kwargs):
        """
        Returns a limited and offset list of both types of contents, filtered
        and in some order.
        """
        contents_results = self._union_of_contents_query(container, **kwargs).all()
        if not expand_models:
            return contents_results

        # partition ids into a map of { component_class names -> list of ids } from the above union query
        id_map: Dict[str, List[int]] = dict(
            [(self.contained_class_type_name, []), (self.subcontainer_class_type_name, [])]
        )
        for result in contents_results:
            result_type = self._get_union_type(result)
            contents_id = self._get_union_id(result)
            if result_type in id_map:
                id_map[result_type].append(contents_id)
            else:
                raise TypeError("Unknown contents type:", result_type)

        # query 2 & 3: use the ids to query each component_class, returning an id->full component model map
        contained_ids = id_map[self.contained_class_type_name]
        id_map[self.contained_class_type_name] = self._contained_id_map(contained_ids)
        subcontainer_ids = id_map[self.subcontainer_class_type_name]
        serialization_params = kwargs.get("serialization_params", None)
        id_map[self.subcontainer_class_type_name] = self._subcontainer_id_map(
            subcontainer_ids, serialization_params=serialization_params
        )

        # cycle back over the union query to create an ordered list of the objects returned in queries 2 & 3 above
        contents = []
        filters = kwargs.get("filters") or []
        # TODO: or as generator?
        for result in contents_results:
            result_type = self._get_union_type(result)
            contents_id = self._get_union_id(result)
            content = id_map[result_type][contents_id]
            if self.passes_filters(content, filters):
                contents.append(content)
        return contents

    @staticmethod
    def passes_filters(content, filters):
        for filter_fn in filters:
            if filter_fn.filter_type == "function":
                if not filter_fn.filter(content):
                    return False
        return True

    def _union_of_contents_query(
        self, container, filters=None, limit=None, offset=None, order_by=None, user_id=None, **kwargs
    ):
        """
        Returns a query for a limited and offset list of both types of contents,
        filtered and in some order.
        """
        order_by = order_by if order_by is not None else self.default_order_by
        order_by = order_by if isinstance(order_by, (tuple, list)) else (order_by,)

        # TODO: 3 queries and 3 iterations over results - this is undoubtedly better solved in the actual SQL layer
        # via one common table for contents, Some Yonder Resplendent and Fanciful Join, or ORM functionality
        # Here's the (bizarre) strategy:
        #   1. create a union of common columns between contents classes - filter, order, and limit/offset this
        #   2. extract the ids returned from 1 for each class, query each content class by that id list
        #   3. use the results/order from 1 to recombine/merge the 2+ query result lists from 2, return that

        # note: I'm trying to keep these private functions as generic as possible in order to move them toward base later

        # query 1: create a union of common columns for which the component_classes can be filtered/limited
        contained_query = self._contents_common_query_for_contained(
            history_id=container.id if container else None, user_id=user_id
        )
        subcontainer_query = self._contents_common_query_for_subcontainer(
            history_id=container.id if container else None, user_id=user_id
        )

        filters = filters or []
        # Apply filters that are specific to a model
        for orm_filter in filters:
            if orm_filter.filter_type == "orm_function":
                contained_query = contained_query.filter(orm_filter.filter(self.contained_class))
                subcontainer_query = subcontainer_query.filter(orm_filter.filter(self.subcontainer_class))
            elif orm_filter.filter_type == "orm":
                contained_query = self._apply_orm_filter(contained_query, orm_filter)
                subcontainer_query = self._apply_orm_filter(subcontainer_query, orm_filter)

        contents_query = contained_query.union_all(subcontainer_query)
        contents_query = contents_query.order_by(*order_by)

        if limit is not None:
            contents_query = contents_query.limit(limit)
        if offset is not None:
            contents_query = contents_query.offset(offset)
        return contents_query

    def _apply_orm_filter(self, qry, orm_filter):
        if isinstance(orm_filter.filter, sql.elements.BinaryExpression):
            for match in filter(lambda col: col["name"] == orm_filter.filter.left.name, qry.column_descriptions):
                column = match["expr"]
                new_filter = orm_filter.filter._clone()
                if orm_filter.case_insensitive:
                    column = func.lower(column)
                new_filter.left = column
                qry = qry.filter(new_filter)
        return qry

    def _contents_common_columns(self, component_class, **kwargs):
        columns = []
        # pull column from class by name or override with kwargs if listed there, then label
        for column_name in self.common_columns:
            if column_name in kwargs:
                column = kwargs.get(column_name, None)
            elif column_name == "model_class":
                column = literal(component_class.__name__)
            else:
                column = getattr(component_class, column_name)
            column = column.label(column_name)
            columns.append(column)
        return columns

    def _contents_common_query_for_contained(self, history_id, user_id):
        component_class = self.contained_class
        # TODO: and now a join with Dataset - this is getting sad
        columns = self._contents_common_columns(
            component_class,
            history_content_type=literal("dataset"),
            size=model.Dataset.file_size,
            state=model.Dataset.state,
            # do not have inner collections
            collection_id=literal(None),
        )
        subquery = self._session().query(*columns)
        # for the HDA's we need to join the Dataset since it has an actual state column
        subquery = subquery.join(model.Dataset, model.Dataset.id == component_class.table.c.dataset_id)
        if history_id:
            subquery = subquery.filter(component_class.table.c.history_id == history_id)
        else:
            # Make sure we only return items that are user-accessible by checking that they are in a history
            # owned by the current user.
            # TODO: move into filter mixin, and implement accessible logic as SQL query
            subquery = subquery.filter(
                component_class.table.c.history_id == model.History.table.c.id, model.History.table.c.user_id == user_id
            )
        return subquery

    def _contents_common_query_for_subcontainer(self, history_id, user_id):
        component_class = self.subcontainer_class
        columns = self._contents_common_columns(
            component_class,
            history_content_type=literal("dataset_collection"),
            # do not have datasets
            dataset_id=literal(None),
            size=literal(None),
            state=model.DatasetCollection.populated_state,
            # TODO: should be purgable? fix
            purged=literal(False),
            extension=literal(None),
        )
        subquery = self._session().query(*columns)
        # for the HDCA's we need to join the DatasetCollection since it has the populated_state
        subquery = subquery.join(model.DatasetCollection, model.DatasetCollection.id == component_class.collection_id)
        if history_id:
            subquery = subquery.filter(component_class.history_id == history_id)
        else:
            subquery = subquery.filter(
                component_class.history_id == model.History.table.c.id, model.History.table.c.user_id == user_id
            )
        return subquery

    def _get_union_type(self, union):
        """Return the string name of the class for this row in the union results"""
        return str(union[1])

    def _get_union_id(self, union):
        """Return the id for this row in the union results"""
        return union[2]

    def _contained_id_map(self, id_list):
        """Return an id to model map of all contained-type models in the id_list."""
        if not id_list:
            return []
        component_class = self.contained_class
        query = (
            self._session()
            .query(component_class)
            .filter(component_class.id.in_(id_list))
            .options(undefer(component_class._metadata))
            .options(joinedload(component_class.dataset).joinedload(model.Dataset.actions))
            .options(joinedload(component_class.tags))
            .options(joinedload(component_class.annotations))  # type: ignore[attr-defined]
        )
        return {row.id: row for row in query.all()}

    def _subcontainer_id_map(self, id_list, serialization_params=None):
        """Return an id to model map of all subcontainer-type models in the id_list."""
        if not id_list:
            return []
        component_class = self.subcontainer_class
        query = (
            self._session()
            .query(component_class)
            .filter(component_class.id.in_(id_list))
            .options(joinedload(component_class.collection))
            .options(joinedload(component_class.tags))
            .options(joinedload(component_class.annotations))
        )

        # This will conditionally join a potentially costly job_state summary
        # All the paranoia if-checking makes me wonder if serialization_params
        # should really be a property of the manager class instance
        if serialization_params and serialization_params.keys:
            if "job_state_summary" in serialization_params.keys:
                query = query.options(joinedload(component_class.job_state_summary))

        return {row.id: row for row in query.all()}


class HistoryContentsSerializer(base.ModelSerializer, deletable.PurgableSerializerMixin):
    """
    Interface/service object for serializing histories into dictionaries.
    """

    model_manager_class = HistoryContentsManager

    def __init__(self, app: MinimalManagerApp, **kwargs):
        super().__init__(app, **kwargs)

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "type_id",
                "history_id",
                "hid",
                "history_content_type",
                "visible",
                "dataset_id",
                "collection_id",
                "name",
                "state",
                "deleted",
                "purged",
                "create_time",
                "update_time",
            ],
        )

    # assumes: outgoing to json.dumps and sanitized
    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)
        serializers: Dict[str, Serializer] = {
            "type_id": self.serialize_type_id,
            "history_id": self.serialize_id,
            "dataset_id": self.serialize_id_or_skip,
            "collection_id": self.serialize_id_or_skip,
        }
        self.serializers.update(serializers)

    def serialize_id_or_skip(self, item: Any, key: str, **context):
        """Serialize id or skip if attribute with `key` is not present."""
        if not hasattr(item, key):
            raise base.SkipAttribute("no such attribute")
        return self.serialize_id(item, key, **context)


class HistoryContentsFilters(
    base.ModelFilterParser,
    annotatable.AnnotatableFilterMixin,
    deletable.PurgableFiltersMixin,
    genomes.GenomeFilterMixin,
    taggable.TaggableFilterMixin,
    tools.ToolFilterMixin,
):
    # surprisingly (but ominously), this works for both content classes in the union that's filtered
    model_class = model.HistoryDatasetAssociation

    def parse_query_filters_with_relations(self, query_filters: ValueFilterQueryParams, history_id):
        """Parse query filters but consider case where related filter is included."""
        if query_filters.q and query_filters.qv and "related-eq" in query_filters.q:
            qv_index = query_filters.q.index("related-eq")
            qv_hid = query_filters.qv[qv_index]

            # Make new q and qv excluding related filter
            new_q = [x for i, x in enumerate(query_filters.q) if i != qv_index]
            new_qv = [x for i, x in enumerate(query_filters.qv) if i != qv_index]

            # Get list of related item hids from job_connections manager
            job_connections_manager = JobConnectionsManager(self.app.model.session)
            related = job_connections_manager.get_related_hids(history_id, qv_hid)

            # Make new query_filters with updated list of related hids for given hid
            new_q.append("related-eq")
            new_qv.append(json.dumps(related))
            query_filters_with_relations = ValueFilterQueryParams(
                q=new_q,
                qv=new_qv,
            )
            return super().parse_query_filters(query_filters_with_relations)
        return super().parse_query_filters(query_filters)

    def _parse_orm_filter(self, attr, op, val):
        # we need to use some manual/text/column fu here since some where clauses on the union don't work
        # using the model_class defined above - they need to be wrapped in their own .column()
        # (and some of these are *not* a normal columns (especially 'state') anyway)
        # TODO: genericize these - can probably extract a _get_column( attr, ... ) or something
        # special cases...special cases everywhere
        def get_filter(attr, op, val):
            if attr == "history_content_type" and op == "eq":
                if val in ("dataset", "dataset_collection"):
                    return sql.column("history_content_type") == val
                raise_filter_err(attr, op, val, "bad op in filter")

            if attr == "related":
                if op == "eq":
                    return sql.column("hid").in_(json.loads(val))
                raise_filter_err(attr, op, val, "bad op in filter")

            if attr == "type_id":
                if op == "eq":
                    return sql.column("type_id") == val
                if op == "in":
                    return sql.column("type_id").in_(self.parse_type_id_list(val))
                raise_filter_err(attr, op, val, "bad op in filter")

            if attr in ("update_time", "create_time"):
                if op == "ge":
                    return sql.column(attr) >= self.parse_date(val)
                if op == "le":
                    return sql.column(attr) <= self.parse_date(val)
                if op == "gt":
                    return sql.column(attr) > self.parse_date(val)
                if op == "lt":
                    return sql.column(attr) < self.parse_date(val)
                raise_filter_err(attr, op, val, "bad op in filter")

            if attr == "state":
                valid_states = model.Dataset.states.values()
                if op == "eq":
                    if val not in valid_states:
                        raise_filter_err(attr, op, val, "invalid state in filter")
                    return sql.column("state") == val
                if op == "in":
                    states = [s for s in val.split(",") if s]
                    for state in states:
                        if state not in valid_states:
                            raise_filter_err(attr, op, state, "invalid state in filter")
                    return sql.column("state").in_(states)
                raise_filter_err(attr, op, val, "bad op in filter")

        column_filter = get_filter(attr, op, val)
        if column_filter is not None:
            return self.parsed_filter(filter_type="orm", filter=column_filter)
        return super()._parse_orm_filter(attr, op, val)

    def decode_type_id(self, type_id):
        TYPE_ID_SEP = "-"
        split = type_id.split(TYPE_ID_SEP, 1)
        return TYPE_ID_SEP.join((split[0], str(self.app.security.decode_id(split[1]))))

    def parse_type_id_list(self, type_id_list_string, sep=","):
        """
        Split `type_id_list_string` at `sep`.
        """
        return [self.decode_type_id(type_id) for type_id in type_id_list_string.split(sep)]

    def _add_parsers(self):
        super()._add_parsers()
        annotatable.AnnotatableFilterMixin._add_parsers(self)
        genomes.GenomeFilterMixin._add_parsers(self)
        deletable.PurgableFiltersMixin._add_parsers(self)
        taggable.TaggableFilterMixin._add_parsers(self)
        tools.ToolFilterMixin._add_parsers(self)
        self.orm_filter_parsers.update(
            {
                "history_content_type": {"op": ("eq")},
                # maybe remove related from here, as there's no corresponding field?
                "related": {"op": ("eq")},
                "type_id": {"op": ("eq", "in"), "val": self.parse_type_id_list},
                "hid": {"op": ("eq", "ge", "le", "gt", "lt"), "val": int},
                # TODO: needs a different val parser - but no way to add to the above
                # 'hid-in'        : { 'op': ( 'in' ), 'val': self.parse_int_list },
                "name": {"op": ("eq", "contains", "like")},
                "state": {"op": ("eq", "in")},
                "visible": {"op": ("eq"), "val": parse_bool},
                "create_time": {"op": ("le", "ge", "lt", "gt"), "val": self.parse_date},
                "update_time": {"op": ("le", "ge", "lt", "gt"), "val": self.parse_date},
            }
        )
