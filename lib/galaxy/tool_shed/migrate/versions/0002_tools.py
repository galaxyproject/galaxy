"""
The Emboss 5.0.0 tools have been eliminated from the distribution and the Emboss datatypes have been removed from
datatypes_conf.xml.sample.  You should remove the Emboss datatypes from your version of datatypes_conf.xml.  The
repositories named emboss_5 and emboss_datatypes from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
will be installed into your local Galaxy instance at the location discussed above by running the following command.

vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
sh ./scripts/migrate_tools/0002_tools.sh
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
"""

import sys

def upgrade():
    print __doc__
def downgrade():
    pass
