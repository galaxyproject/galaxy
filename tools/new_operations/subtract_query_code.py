from galaxy.datatypes import *

#return set of columns contained in both input datasets
def get_columns( input1, input2 ):
    columns = []
    """
    Placing a '?' in the first option will keep 'c1' from being automatically
    selected if the user does nothing.  Not sure why this is the behavior...
    """
    columns.append(('?','None',False))
    if isinstance(input1.datatype, tabular.Tabular().__class__) and isinstance(input2.datatype, tabular.Tabular().__class__):
        num_columns = min(input1.metadata.columns, input2.metadata.columns)
        for col in range(1, num_columns+1):
            option = "c" + str(col)
            columns.append((option,str(col),False))
    return columns