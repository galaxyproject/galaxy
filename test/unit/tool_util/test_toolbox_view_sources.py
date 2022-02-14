import json
import os
import shutil
import tempfile

from galaxy.tool_util.toolbox.views.sources import StaticToolBoxViewSources
from galaxy.util import safe_makedirs
from .test_toolbox_view_parsing import EXAMPLE_1


def test_from_dicts():
    sources = StaticToolBoxViewSources(view_dicts=[EXAMPLE_1])
    defs = sources.get_definitions()
    assert len(defs) == 1
    assert defs[0].id == "rna"


def test_from_directory():
    target_dir = tempfile.mkdtemp()
    dir_1 = os.path.join(target_dir, "dir1")
    dir_2 = os.path.join(target_dir, "dir2")
    safe_makedirs(dir_1)
    safe_makedirs(dir_2)
    with open(os.path.join(dir_1, "foo.json"), "w") as f:
        json.dump(EXAMPLE_1, f)
    with open(os.path.join(dir_2, "seqanalysis.yml"), "w") as f:
        f.write(
            """
name: Sequence Analysis
type: generic
items:
- type: workflow
  id: 12345abcd
"""
        )

    config_param = f"{os.path.abspath(dir_1)},{os.path.abspath(dir_2)}"
    try:
        sources = StaticToolBoxViewSources(view_directories=config_param)
        defs = sources.get_definitions()
        assert len(defs) == 2
        assert defs[0].id == "rna"
        assert defs[1].id == "seqanalysis"
    finally:
        shutil.rmtree(target_dir)
