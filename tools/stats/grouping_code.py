
def get_columns( input1 ):
    columns = []

    for col in range(1, input1.metadata.columns+1):
        option = "c" + str(col)
        columns.append((option,str(col),False))
    return columns
