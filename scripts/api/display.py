#!/usr/bin/env python
from __future__ import print_function

import os
import sys

from six.moves.urllib.error import URLError

from common import display

try:
    display( *sys.argv[1:3] )
except TypeError as e:
    print('usage: %s key url' % os.path.basename( sys.argv[0] ))
    print(e)
    sys.exit( 1 )
except URLError as e:
    print(e)
    sys.exit( 1 )
