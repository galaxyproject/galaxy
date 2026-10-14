#!/usr/bin/env python
"""Standalone CLI entry for the tool source store populator.

Delegates to the installed :func:`galaxy.tools.source_store.populator.main`.
All flags, including
``--watch``, are documented on that function's argparse setup.

Installations using the ``galaxy-app`` package should prefer the
``galaxy-populate-tool-source-store`` console script it installs; in-process
callers should import the populator module directly.
"""

from galaxy.tools.source_store.populator import main

if __name__ == "__main__":
    main()
