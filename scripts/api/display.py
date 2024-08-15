#!/usr/bin/env python

import os
import sys
from urllib.error import URLError

from common import display  # noqa: I100,I202

try:
    display(*sys.argv[1:3])
except TypeError as e:
    print(f"usage: {os.path.basename(sys.argv[0])} key url")
    print(e)
    sys.exit(1)
except URLError as e:
    print(e)
    sys.exit(1)
