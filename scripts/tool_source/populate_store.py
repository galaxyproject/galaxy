#!/usr/bin/env python
"""Standalone CLI entry for the tool source store populator.

Thin shim: extends ``sys.path`` so ``galaxy.*`` resolves when the script is
invoked directly (no venv-installed galaxy package required), then delegates
to :func:`galaxy.tools.source_store.populator.main`. All flags, including
``--watch``, are documented on that function's argparse setup.

Installations using the ``galaxy-app`` package should prefer the
``galaxy-populate-tool-source-store`` console script it installs; in-process
callers should import the populator module directly.
"""

import sys
from pathlib import Path

galaxy_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tools.source_store.populator import main

if __name__ == "__main__":
    main()
