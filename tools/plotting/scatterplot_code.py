
def get_columns( input ):
    columns = []
    elems = []

    for i, line in enumerate( file ( input.file_name ) ):
        valid = True
        if line and not line.startswith( '#' ): 
            line = line.rstrip('\r\n')
            elems = line.split( '\t' )
    
            """
            Since this tool requires users to select only those columns
            that contain numerical values, we'll restrict the column select
            list appropriately.
            """
            if len(elems) > 0:
                for col in range(1, input.metadata.columns+1):
                    try:
                        val = float(elems[col-1])
                    except:
                        val = elems[col-1]
                        if val:
                            if val.strip().lower() != "na":
                                valid = False
                        else:
                            valid = False
                    if valid:
                        option = "c" + str(col)
                        columns.append((option,str(col),False))
            if len(columns) > 0:
                """
                We have our select list built, so we can break out of the outer most for loop
                """
                break 
        if i == 30:
            break # Hopefully we never get here...

    return columns