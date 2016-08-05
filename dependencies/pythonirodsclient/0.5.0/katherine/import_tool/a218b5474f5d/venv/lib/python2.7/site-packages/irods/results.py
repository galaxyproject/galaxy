from prettytable import PrettyTable

from irods.models import ModelBase

class ResultSet(object):
    def __init__(self, raw):
        self.length = raw.rowCnt
        col_length = raw.attriCnt
        self.cols = raw.SqlResult_PI[:col_length]
        self.rows = [self._format_row(i) for i in range(self.length)]
        try:
            self.continue_index = raw.continueInx
        except KeyError:
            self.continue_index = 0

    def __str__(self):
        table = PrettyTable()
        for col in self.cols:
            table.add_column(ModelBase.columns[col.attriInx].icat_key, col.value)
        table.align = 'l'
        return table.get_string().encode('utf-8')

    def _format_row(self, index):
        values = [(col, col.value[index]) for col in self.cols]

        def format(attribute_index, value):
            col = ModelBase.columns[attribute_index]
            try:
                return (col, col.type.to_python(value))
            except (TypeError, ValueError):
                return (col, value)
            
        return dict([format(col.attriInx, value) for col, value in values])

    def __getitem__(self, index):
        return self.rows.__getitem__(index)

    def __iter__(self):
        return self.rows.__iter__()

    def __len__(self):
        return self.length
    
    # For testing. Might go somewhere else...
    def has_value(self, value):
        found = False
        
        for row in self.rows:
            if value in row.values():
                found = True
                
        return found
        
