"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""
import logging

from sqlalchemy import (
    asc,
    desc,
    false,
    func,
    literal,
    sql,
    true
)
from sqlalchemy.orm import (
    eagerload,
    undefer
)

from galaxy import (
    exceptions as glx_exceptions,
    model
)
from galaxy.managers import (
    base,
    containers,
    deletable,
    hdas,
    hdcas
)

log = logging.getLogger(__name__)


# into its own class to have it's own filters, etc.
# TODO: but can't inherit from model manager (which assumes only one model)
class HistoryContentsManager(containers.ContainerManagerMixin):

    root_container_class = model.History

    contained_class = model.HistoryDatasetAssociation
    contained_class_manager_class = hdas.HDAManager
    contained_class_type_name = 'dataset'

    subcontainer_class = model.HistoryDatasetCollectionAssociation
    subcontainer_class_manager_class = hdcas.HDCAManager
    subcontainer_class_type_name = 'dataset_collection'

    #: the columns which are common to both subcontainers and non-subcontainers.
    #  (Also the attributes that may be filtered or orderered_by)
    common_columns = (
        "history_id",
        "history_content_type",
        "id",
        "type_id",
        "hid",
        # joining columns
        "dataset_id",
        "collection_id",
        "name",
        "state",
        "deleted",
        "purged",
        "visible",
        "create_time",
        "update_time",
    )
    default_order_by = 'hid'

    def __init__(self, app):
        self.app = app
        self.contained_manager = self.contained_class_manager_class(app)
        self.subcontainer_manager = self.subcontainer_class_manager_class(app)

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
        return self._union_of_contents(container,
            filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs)

    def contents_count(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns a count of both/all types of contents, based on the given filters.
        """
        return self.contents_query(container,
            filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs).count()

    def contents_query(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns the contents union query for subqueries, etc.
        """
        return self._union_of_contents_query(container,
            filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs)

    # order_by parsing - similar to FilterParser but not enough yet to warrant a class?
    def parse_order_by(self, order_by_string, default=None):
        """Return an ORM compatible order_by using the given string"""
        if order_by_string in ('hid', 'hid-dsc'):
            return desc('hid')
        if order_by_string == 'hid-asc':
            return asc('hid')
        if order_by_string in ('create_time', 'create_time-dsc'):
            return desc('create_time')
        if order_by_string == 'create_time-asc':
            return asc('create_time')
        if order_by_string in ('update_time', 'update_time-dsc'):
            return desc('update_time')
        if order_by_string == 'update_time-asc':
            return asc('update_time')
        if order_by_string in ('name', 'name-asc'):
            return asc('name')
        if order_by_string == 'name-dsc':
            return desc('name')
        if default:
            return self.parse_order_by(default)
        # TODO: allow order_by None
        raise glx_exceptions.RequestParameterInvalidException('Unknown order_by', order_by=order_by_string,
            available=['create_time', 'update_time', 'name', 'hid'])

    # history specific methods
    def state_counts(self, history):
        """
        Return a dictionary containing the counts of all contents in each state
        keyed by the distinct states.

        Note: does not include deleted/hidden contents.
        """
        filters = [
            sql.column('deleted') == false(),
            sql.column('visible') == true()
        ]
        contents_subquery = self._union_of_contents_query(history, filters=filters).subquery()
        statement = (sql.select([sql.column('state'), func.count('*')])
            .select_from(contents_subquery)
            .group_by(sql.column('state')))
        counts = self.app.model.context.execute(statement).fetchall()
        return dict(counts)

    def active_counts(self, history):
        """
        Return a dictionary keyed with 'deleted', 'hidden', and 'active' with values
        for each representing the count of contents in each state.

        Note: counts for deleted and hidden overlap; In other words, a dataset that's
        both deleted and hidden will be added to both totals.
        """
        returned = dict(deleted=0, hidden=0, active=0)
        contents_subquery = self._union_of_contents_query(history).subquery()
        columns = [
            sql.column('deleted'),
            sql.column('visible'),
            func.count('*')
        ]
        statement = (sql.select(columns)
            .select_from(contents_subquery)
            .group_by(sql.column('deleted'), sql.column('visible')))
        groups = self.app.model.context.execute(statement).fetchall()
        for deleted, visible, count in groups:
            if deleted:
                returned['deleted'] += count
            if not visible:
                returned['hidden'] += count
            if not deleted and visible:
                returned['active'] += count
        return returned

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
        id_map = dict(((self.contained_class_type_name, []), (self.subcontainer_class_type_name, [])))
        for result in contents_results:
            result_type = self._get_union_type(result)
            contents_id = self._get_union_id(result)
            if result_type in id_map:
                id_map[result_type].append(contents_id)
            else:
                raise TypeError('Unknown contents type:', result_type)

        # query 2 & 3: use the ids to query each component_class, returning an id->full component model map
        contained_ids = id_map[self.contained_class_type_name]
        id_map[self.contained_class_type_name] = self._contained_id_map(contained_ids)
        subcontainer_ids = id_map[self.subcontainer_class_type_name]
        id_map[self.subcontainer_class_type_name] = self._subcontainer_id_map(subcontainer_ids)

        # cycle back over the union query to create an ordered list of the objects returned in queries 2 & 3 above
        contents = []
        # TODO: or as generator?
        for result in contents_results:
            result_type = self._get_union_type(result)
            contents_id = self._get_union_id(result)
            content = id_map[result_type][contents_id]
            contents.append(content)
        return contents

    def _union_of_contents_query(self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs):
        """
        Returns a query for a limited and offset list of both types of contents,
        filtered and in some order.
        """
        order_by = order_by if order_by is not None else self.default_order_by
        order_by = order_by if isinstance(order_by, (tuple, list)) else (order_by, )

        # TODO: 3 queries and 3 iterations over results - this is undoubtedly better solved in the actual SQL layer
        # via one common table for contents, Some Yonder Resplendent and Fanciful Join, or ORM functionality
        # Here's the (bizarre) strategy:
        #   1. create a union of common columns between contents classes - filter, order, and limit/offset this
        #   2. extract the ids returned from 1 for each class, query each content class by that id list
        #   3. use the results/order from 1 to recombine/merge the 2+ query result lists from 2, return that

        # note: I'm trying to keep these private functions as generic as possible in order to move them toward base later

        # query 1: create a union of common columns for which the component_classes can be filtered/limited
        contained_query = self._contents_common_query_for_contained(container.id)
        subcontainer_query = self._contents_common_query_for_subcontainer(container.id)
        contents_query = contained_query.union(subcontainer_query)

        # TODO: this needs the same fn/orm split that happens in the main query
        for orm_filter in (filters or []):
            contents_query = contents_query.filter(orm_filter)
        contents_query = contents_query.order_by(*order_by)

        if limit is not None:
            contents_query = contents_query.limit(limit)
        if offset is not None:
            contents_query = contents_query.offset(offset)
        return contents_query

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

    def _contents_common_query_for_contained(self, history_id):
        component_class = self.contained_class
        # TODO: and now a join with Dataset - this is getting sad
        columns = self._contents_common_columns(component_class,
            history_content_type=literal('dataset'),
            state=model.Dataset.state,
            # do not have inner collections
            collection_id=literal(None)
        )
        subquery = self._session().query(*columns)
        # for the HDA's we need to join the Dataset since it has an actual state column
        subquery = subquery.join(model.Dataset, model.Dataset.id == component_class.dataset_id)
        subquery = subquery.filter(component_class.history_id == history_id)
        return subquery

    def _contents_common_query_for_subcontainer(self, history_id):
        component_class = self.subcontainer_class
        columns = self._contents_common_columns(component_class,
            history_content_type=literal('dataset_collection'),
            # do not have datasets
            dataset_id=literal(None),
            state=model.DatasetCollection.populated_state,
            # TODO: should be purgable? fix
            purged=literal(False),
            # these are attached instead to the inner collection joined below
            create_time=model.DatasetCollection.create_time,
            update_time=model.DatasetCollection.update_time
        )
        subquery = self._session().query(*columns)
        # for the HDCA's we need to join the DatasetCollection since it has update/create times
        subquery = subquery.join(model.DatasetCollection,
            model.DatasetCollection.id == component_class.collection_id)
        subquery = subquery.filter(component_class.history_id == history_id)
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
        query = (self._session().query(component_class)
            .filter(component_class.id.in_(id_list))
            .options(undefer('_metadata'))
            .options(eagerload('dataset.actions'))
            .options(eagerload('tags'))
            .options(eagerload('annotations')))
        return dict((row.id, row) for row in query.all())

    def _subcontainer_id_map(self, id_list):
        """Return an id to model map of all subcontainer-type models in the id_list."""
        if not id_list:
            return []
        component_class = self.subcontainer_class
        query = (self._session().query(component_class)
            .filter(component_class.id.in_(id_list))
            .options(eagerload('collection'))
            .options(eagerload('tags'))
            .options(eagerload('annotations')))
        return dict((row.id, row) for row in query.all())


class HistoryContentsSerializer(base.ModelSerializer, deletable.PurgableSerializerMixin):
    """
    Interface/service object for serializing histories into dictionaries.
    """
    model_manager_class = HistoryContentsManager

    def __init__(self, app, **kwargs):
        super(HistoryContentsSerializer, self).__init__(app, **kwargs)

        self.default_view = 'summary'
        self.add_view('summary', [
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
        ])

    # assumes: outgoing to json.dumps and sanitized
    def add_serializers(self):
        super(HistoryContentsSerializer, self).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        self.serializers.update({
            'type_id'       : self.serialize_type_id,
            'history_id'    : self.serialize_id,
            'dataset_id'    : self.serialize_id_or_skip,
            'collection_id' : self.serialize_id_or_skip,
        })

    def serialize_id_or_skip(self, content, key, **context):
        """Serialize id or skip if attribute with `key` is not present."""
        if not hasattr(content, key):
            raise base.SkipAttribute('no such attribute')
        return self.serialize_id(content, key, **context)


class HistoryContentsFilters(base.ModelFilterParser, deletable.PurgableFiltersMixin):
    # surprisingly (but ominously), this works for both content classes in the union that's filtered
    model_class = model.HistoryDatasetAssociation

    # TODO: history_content_type filter doesn't work with psycopg2: column does not exist (even with hybrid props)
    def _parse_orm_filter(self, attr, op, val):

        def raise_filter_err(attr, op, val, msg):
            raise glx_exceptions.RequestParameterInvalidException(msg, column=attr, operation=op, val=val)

        # we need to use some manual/text/column fu here since some where clauses on the union don't work
        # using the model_class defined above - they need to be wrapped in their own .column()
        # (and some of these are *not* a normal columns (especially 'state') anyway)
        # TODO: genericize these - can probably extract a _get_column( attr, ... ) or something
        # special cases...special cases everywhere
        if attr == 'history_content_type' and op == 'eq':
            if val == 'dataset':
                return sql.column('history_content_type') == 'dataset'
            if val == 'dataset_collection':
                return sql.column('history_content_type') == 'dataset_collection'
            raise_filter_err(attr, op, val, 'bad op in filter')

        if attr == 'type_id':
            if op == 'eq':
                return sql.column('type_id') == val
            if op == 'in':
                return sql.column('type_id').in_(self.parse_type_id_list(val))
            raise_filter_err(attr, op, val, 'bad op in filter')

        if attr in ('update_time', 'create_time'):
            if op == 'ge':
                return sql.column(attr) >= self.parse_date(val)
            if op == 'le':
                return sql.column(attr) <= self.parse_date(val)
            raise_filter_err(attr, op, val, 'bad op in filter')

        if attr == 'state':
            valid_states = model.Dataset.states.values()
            if op == 'eq':
                if val not in valid_states:
                    raise_filter_err(attr, op, val, 'invalid state in filter')
                return sql.column('state') == val
            if op == 'in':
                states = [s for s in val.split(',') if s]
                for state in states:
                    if state not in valid_states:
                        raise_filter_err(attr, op, state, 'invalid state in filter')
                return sql.column('state').in_(states)
            raise_filter_err(attr, op, val, 'bad op in filter')

        return super(HistoryContentsFilters, self)._parse_orm_filter(attr, op, val)

    def decode_type_id(self, type_id):
        TYPE_ID_SEP = '-'
        split = type_id.split(TYPE_ID_SEP, 1)
        return TYPE_ID_SEP.join([split[0], str(self.app.security.decode_id(split[1]))])

    def parse_type_id_list(self, type_id_list_string, sep=','):
        """
        Split `type_id_list_string` at `sep`.
        """
        return [self.decode_type_id(type_id) for type_id in type_id_list_string.split(sep)]

    def _add_parsers(self):
        super(HistoryContentsFilters, self)._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers(self)
        self.orm_filter_parsers.update({
            'history_content_type' : {'op': ('eq')},
            'type_id'       : {'op': ('eq', 'in'), 'val': self.parse_type_id_list},
            'hid'           : {'op': ('eq', 'ge', 'le'), 'val': int},
            # TODO: needs a different val parser - but no way to add to the above
            # 'hid-in'        : { 'op': ( 'in' ), 'val': self.parse_int_list },
            'name'          : {'op': ('eq', 'contains', 'like')},
            'state'         : {'op': ('eq', 'in')},
            'visible'       : {'op': ('eq'), 'val': self.parse_bool},
            'create_time'   : {'op': ('le', 'ge'), 'val': self.parse_date},
            'update_time'   : {'op': ('le', 'ge'), 'val': self.parse_date},
        })
