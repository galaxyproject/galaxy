"""
The following tools have been eliminated from the distribution:
Add column to an existing dataset, Change Case of selected columns, 
Condense consecutive characters, Convert delimiters to TAB, 
Cut columns from a table, Merge Columns together, Remove beginning of a file, 
Select first lines from a dataset, Select last lines from a dataset, 
and Trim leading or trailing characters.  The tools are now available in the 
repositories named add_value, change_case, condense_characters, 
convert_characters, cut_columns, merge_cols, remove_beginning, 
show_beginning, show_tail, and trimmer from the main Galaxy tool shed at 
http://toolshed.g2.bx.psu.edu, and will be installed into your 
local Galaxy instance at the location discussed above by running 
the following command.
"""

import sys

def upgrade():
    print __doc__
def downgrade():
    pass
