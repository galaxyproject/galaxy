from collections import OrderedDict

from irods.models import Model
from irods.column import Column, Keyword
from irods.message import (
    IntegerIntegerMap, IntegerStringMap, StringStringMap,
    GenQueryRequest, GenQueryResponse, empty_gen_query_out,
    iRODSMessage)
from irods.api_number import api_number
from irods.exception import CAT_NO_ROWS_FOUND, MultipleResultsFound, NoResultFound
from irods.results import ResultSet

query_number = {'ORDER_BY': 0x400,
                'ORDER_BY_DESC': 0x800,
                'RETURN_TOTAL_ROW_COUNT': 0x20,
                'NO_DISTINCT': 0x40,
                'QUOTA_QUERY': 0x80,
                'AUTO_CLOSE': 0x100,
                'UPPER_CASE_WHERE': 0x200,
                'SELECT_MIN': 2,
                'SELECT_MAX': 3,
                'SELECT_SUM': 4,
                'SELECT_AVG': 5,
                'SELECT_COUNT': 6}

# Not present in iRODS 3.3.1 and older
new_icat_keys = ['D_RESC_HIER',
                 'R_FREE_SPACE_TIME',
                 'R_RESC_STATUS',
                 'R_RESC_CHILDREN',
                 'R_RESC_CONTEXT',
                 'R_RESC_PARENT',
                 'R_RESC_OBJCOUNT']


class Query(object):

    def __init__(self, sess, *args, **kwargs):
        self.sess = sess
        self.columns = OrderedDict()
        self.criteria = []
        self._limit = -1
        self._offset = 0
        self._continue_index = 0

        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Model):
                for col in arg._columns:
                    self.columns[col] = 1
            elif isinstance(arg, Column):
                self.columns[arg] = 1
            else:
                raise TypeError("Arguments must be models or columns")

    def _clone(self):
        new_q = Query(self.sess)
        new_q.columns = self.columns
        new_q.criteria = self.criteria
        new_q._limit = self._limit
        new_q._offset = self._offset
        new_q._continue_index = self._continue_index
        return new_q

    def filter(self, *criteria):
        new_q = self._clone()
        new_q.criteria += list(criteria)
        return new_q

    def order_by(self, column, order='asc'):
        new_q = self._clone()
        del new_q.columns[column]
        if order == 'asc':
            new_q.columns[column] = query_number['ORDER_BY']
        elif order == 'desc':
            new_q.columns[column] = query_number['ORDER_BY_DESC']
        else:
            raise ValueError("Ordering must be 'asc' or 'desc'")
        return new_q

    def limit(self, limit):
        new_q = self._clone()
        new_q._limit = limit
        return new_q

    def offset(self, offset):
        new_q = self._clone()
        new_q._offset = offset
        return new_q

    def continue_index(self, continue_index):
        new_q = self._clone()
        new_q._continue_index = continue_index
        return new_q

    def _aggregate(self, func, *args):
        new_q = self._clone()
        # NOTE(wtakase): Override existing column by aggregation.
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Model):
                for col in arg._columns:
                    self.columns[col] = func
            elif isinstance(arg, Column):
                self.columns[arg] = func
            else:
                raise TypeError("Arguments must be models or columns")
        new_q.columns = self.columns
        return new_q

    def min(self, *args):
        return self._aggregate(query_number['SELECT_MIN'], *args)

    def max(self, *args):
        return self._aggregate(query_number['SELECT_MAX'], *args)

    def sum(self, *args):
        return self._aggregate(query_number['SELECT_SUM'], *args)

    def avg(self, *args):
        return self._aggregate(query_number['SELECT_AVG'], *args)

    def count(self, *args):
        return self._aggregate(query_number['SELECT_COUNT'], *args)

    def _select_message(self):
        dct = OrderedDict([(column.icat_id, value)
                           for (column, value) in self.columns.iteritems()])
        return IntegerIntegerMap(dct)

    # todo store criterion for columns and criterion for keywords in seaparate
    # lists
    def _conds_message(self):
        dct = dict([
            (criterion.query_key.icat_id, criterion.op + ' ' + criterion.value)
            for criterion in self.criteria
            if isinstance(criterion.query_key, Column)
        ])
        return IntegerStringMap(dct)

    def _kw_message(self):
        dct = dict([
            (criterion.query_key.icat_key,
             criterion.op + ' ' + criterion.value)
            for criterion in self.criteria
            if isinstance(criterion.query_key, Keyword)
        ])
        return StringStringMap(dct)

    def _message(self):
        max_rows = 500 if self._limit == -1 else self._limit
        args = {
            'maxRows': max_rows,
            'continueInx': self._continue_index,
            'partialStartIndex': self._offset,
            'options': 0,
            'KeyValPair_PI': self._kw_message(),
            'InxIvalPair_PI': self._select_message(),
            'InxValPair_PI': self._conds_message()
        }
        return GenQueryRequest(**args)

    def _strip(self):
        '''For backward compatibility with pre iRODS 4 versions.
        '''
        for column in self.columns:
            if column.icat_key in new_icat_keys:
                del self.columns[column]

    def execute(self):
        with self.sess.pool.get_connection() as conn:
            # check server version
            server_version = tuple(int(token)
                                   for token in conn.server_version.replace('rods', '').split('.'))
            if server_version < (4, 0, 0):
                self._strip()

            message_body = self._message()
            message = iRODSMessage(
                'RODS_API_REQ', msg=message_body, int_info=api_number['GEN_QUERY_AN'])

            conn.send(message)
            try:
                result_message = conn.recv()
                results = result_message.get_main_message(GenQueryResponse)
                result_set = ResultSet(results)
            except CAT_NO_ROWS_FOUND:
                result_set = ResultSet(
                    empty_gen_query_out(self.columns.keys()))
        return result_set

    def close(self):
        '''Closes an open query on the server side.
        self._continue_index must be set to a valid value (returned by a previous query API call).
        '''
        self.limit(0).execute()

    def all(self):
        result_set = self.execute()
        if result_set.continue_index > 0:
            self.continue_index(result_set.continue_index).close()
        return result_set

    def get_batches(self):
        result_set = self.execute()
        yield result_set

        while result_set.continue_index > 0:
            result_set = self.continue_index(
                result_set.continue_index).execute()
            yield result_set

    def get_results(self):
        for result_set in self.get_batches():
            for result in result_set:
                yield result

    def one(self):
        results = self.execute()
        if not len(results):
            raise NoResultFound()
        if len(results) > 1:
            raise MultipleResultsFound()
        return results[0]

    def first(self):
        query = self.limit(1)
        results = query.execute()
        if not len(results):
            return None
        else:
            return results[0]

#     def __getitem__(self, val):
#         pass
