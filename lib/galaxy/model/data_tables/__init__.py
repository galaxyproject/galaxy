"""
Galaxy database data tables model classes
"""
import logging

from galaxy.model import RepresentById

log = logging.getLogger(__name__)


# Data Table in database
class DataTable(RepresentById):
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name
        log.debug("DataTable: Loaded a data table '%s'" % name)


class DataTableColumn(RepresentById):
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name


class DataTableColumnAssociation(RepresentById):
    def __init__(self, id=None, data_table_id=None, data_table_column_id=None):
        self.id = id
        self.data_table_id = data_table_id
        self.data_table_column_id = data_table_column_id


class DataTableRow(RepresentById):
    def __init__(self, id=None):
        self.id = id


class DataTableRowAssociation(RepresentById):
    def __init__(self, id=None, data_table_id=None, data_table_row_id=None):
        self.id = id
        self.data_table_id = data_table_id
        self.data_table_row_id = data_table_row_id


class DataTableField(RepresentById):
    def __init__(self, id=None, value=None, data_table_row_id=None, data_table_column_id=None):
        self.id = id
        self.value = value
        self.data_table_row_id = data_table_row_id
        self.data_table_column_id = data_table_column_id
