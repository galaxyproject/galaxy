from json import loads

from galaxy.datatypes.tabular import Tabular
from galaxy.model import DatasetInstance


class BaseDataProvider:
    """
    Base class for data providers. Data providers both:

    - read and package data from datasets
    - write subsets of data to new datasets

    """

    original_dataset: DatasetInstance

    def __init__(
        self,
        converted_dataset=None,
        original_dataset=None,
        dependencies=None,
        error_max_vals="Only the first %i values are returned.",
    ):
        """Create basic data provider."""
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        self.dependencies = dependencies
        self.error_max_vals = error_max_vals


class ColumnDataProvider(BaseDataProvider):
    """Data provider for columnar data"""

    MAX_LINES_RETURNED = 30000

    def __init__(self, original_dataset, max_lines_returned=MAX_LINES_RETURNED):
        # Compatibility check.
        if not isinstance(original_dataset.datatype, Tabular):
            raise Exception("Data provider can only be used with tabular data")

        # Attribute init.
        self.original_dataset = original_dataset
        # allow throttling
        self.max_lines_returned = max_lines_returned

    def get_data(self, columns=None, start_val=0, max_vals=None, skip_comments=True, **kwargs):
        """
        Returns data from specified columns in dataset. Format is list of lists
        where each list is a line of data.
        """
        if not columns:
            raise TypeError("parameter required: columns")

        # TODO: validate kwargs
        try:
            max_vals = int(max_vals)
            max_vals = min([max_vals, self.max_lines_returned])
        except (ValueError, TypeError):
            max_vals = self.max_lines_returned

        try:
            start_val = int(start_val)
            start_val = max([start_val, 0])
        except (ValueError, TypeError):
            start_val = 0

        # skip comment lines (if any/avail)
        # pre: should have original_dataset and
        if (
            skip_comments
            and self.original_dataset.metadata.comment_lines
            and start_val < self.original_dataset.metadata.comment_lines
        ):
            start_val = int(self.original_dataset.metadata.comment_lines)

        # columns is an array of ints for now (should handle column names later)
        columns = loads(columns)
        for column in columns:
            assert (column < self.original_dataset.metadata.columns) and (
                column >= 0
            ), "column index (%d) must be positive and less" % (column) + " than the number of columns: %d" % (
                self.original_dataset.metadata.columns
            )

        # set up the response, column lists
        response = {}
        response["data"] = data = [[] for column in columns]
        response["meta"] = meta = [{"min": None, "max": None, "count": 0, "sum": 0} for column in columns]

        column_types = [self.original_dataset.metadata.column_types[column] for column in columns]

        # function for casting by column_types
        def cast_val(val, type):
            """Cast value based on type. Return None if can't be cast"""
            if type == "int":
                try:
                    val = int(val)
                except ValueError:
                    return None
            elif type == "float":
                try:
                    val = float(val)
                except ValueError:
                    return None
            return val

        returning_data = False
        f = open(self.original_dataset.get_file_name())
        # TODO: add f.seek if given fptr in kwargs
        for count, line in enumerate(f):
            # check line v. desired start, end
            if count < start_val:
                continue
            if (count - start_val) >= max_vals:
                break

            returning_data = True

            fields = line.split()
            fields_len = len(fields)
            # NOTE: this will return None/null for abberrant column values (including bad indeces)
            for index, column in enumerate(columns):
                column_val = None
                column_type = column_types[index]
                if column < fields_len:
                    column_val = cast_val(fields[column], column_type)
                    if column_val is not None:
                        # if numeric, maintain min, max, sum
                        if column_type == "float" or column_type == "int":
                            if (meta[index]["min"] is None) or (column_val < meta[index]["min"]):
                                meta[index]["min"] = column_val

                            if (meta[index]["max"] is None) or (column_val > meta[index]["max"]):
                                meta[index]["max"] = column_val

                            meta[index]["sum"] += column_val

                # maintain a count - for other stats
                meta[index]["count"] += 1
                data[index].append(column_val)

        response["endpoint"] = dict(last_line=(count - 1), file_ptr=f.tell())
        f.close()

        if not returning_data:
            return None

        for index, meta in enumerate(response["meta"]):
            column_type = column_types[index]
            count = meta["count"]

            if (column_type == "float" or column_type == "int") and count:
                meta["mean"] = float(meta["sum"]) / count

                sorted_data = sorted(response["data"][index])
                middle_index = (count / 2) - 1
                if count % 2 == 0:
                    meta["median"] = (sorted_data[middle_index] + sorted_data[(middle_index + 1)]) / 2.0

                else:
                    meta["median"] = sorted_data[middle_index]

        # ugh ... metadata_data_lines is not a reliable source; hafta have an EOF
        return response
