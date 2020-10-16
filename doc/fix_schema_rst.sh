#!/bin/sh
sed -i.bak -e 's|.. code:: xml|.. code-block:: xml|g' $1
# Insert table of contents
sed -i.bak -e '/^``tool``$/i\
.. contents:: Table of contents\
\   :local:\
\   :depth: 1\
..\
\
' $1
rm -f $1.bak
