#!/usr/bin/env python2.4

from fetch_eggs import get_egg_platform
(platform, ucs, noarch) = get_egg_platform()
print platform

