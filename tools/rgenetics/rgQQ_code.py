# before running the qc, need to rename various output files
#       <data format="html" name="html_file" />
#       <data format="txt" name="log_file" parent="html_file" />
#       <data format="tabular" name="marker_file" parent="html_file" />
#       <data format="tabular" name="subject_file" parent="html_file" />

from galaxy import datatypes,model
import sys,string

def get_columns( input ):
    columns = []
    elems = []
    if input and input.metadata.columns:
        ncols = input.metadata.columns
        colnames = ['Col%d' % x for x in range(1,ncols+1)]
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
                    for col in range(len(elems)): # zero offset
                       if i == 0: # header row
                          colnames[col] = elems[col]
                       else:
                          val = elems[col]
                          try:
                              val = float(val)
                              valid = True
                          except:
                              valid = False
                       if valid:
                            option = colnames[col]
                            columns.append((option,str(col),False))
                if len(columns) > 0:
                    """
                    We have our select list built, so we can break out of the outer most for loop
                    """
                    break
            if i == 30:
                break # Hopefully we never get here...
    else:
        columns = [('?','?',False),]
    return columns
