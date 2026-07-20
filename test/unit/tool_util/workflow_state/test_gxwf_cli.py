"""Integration tests for the unified gxwf CLI entry point."""

import os

import pytest

from galaxy.tool_util.workflow_state.scripts.gxwf import main

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
CLEAN_WF = os.path.join(FIXTURES_DIR, "synthetic-cat1-clean.ga")
FORMAT2_WF = os.path.join(FIXTURES_DIR, "synthetic-cat1.gxwf.yml")


def _run(argv, expected_exit=None):
    """Call main() and return exit code; optionally assert it."""
    try:
        main(argv)
        code = 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    if expected_exit is not None:
        assert code == expected_exit, f"expected exit {expected_exit}, got {code}"
    return code


def test_gxwf_help():
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_gxwf_validate_help():
    with pytest.raises(SystemExit) as exc_info:
        main(["validate", "--help"])
    assert exc_info.value.code == 0


def test_gxwf_subcommand_list_in_help(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for cmd in [
        "validate",
        "clean",
        "lint",
        "convert",
        "roundtrip",
        "validate-tree",
        "clean-tree",
        "lint-tree",
        "convert-tree",
        "roundtrip-tree",
    ]:
        assert cmd in out, f"subcommand '{cmd}' not found in --help output"


def test_gxwf_validate():
    _run(["validate", CLEAN_WF], expected_exit=0)


def test_gxwf_validate_nonzero_on_stale():
    """Stale workflow should exit non-zero from validate."""
    stale_wf = os.path.join(FIXTURES_DIR, "synthetic-cat1-stale.ga")
    code = _run(["validate", stale_wf])
    assert code != 0


def test_gxwf_clean():
    _run(["clean", CLEAN_WF], expected_exit=0)


def test_gxwf_clean_preserve_bookkeeping():
    _run(["clean", "--preserve-bookkeeping", CLEAN_WF], expected_exit=0)


def test_gxwf_clean_bookkeeping_flags_mutually_exclusive():
    """--preserve-bookkeeping and --strip-bookkeeping cannot be combined."""
    with pytest.raises(SystemExit) as exc_info:
        main(["clean", "--preserve-bookkeeping", "--strip-bookkeeping", CLEAN_WF])
    assert exc_info.value.code != 0


def test_gxwf_clean_rejects_removed_category_flags():
    """The old per-category --preserve/--strip flags are gone."""
    with pytest.raises(SystemExit) as exc_info:
        main(["clean", "--preserve", "bookkeeping", CLEAN_WF])
    assert exc_info.value.code != 0


def test_gxwf_lint():
    # exit 1 = warnings only (best-practice); exit 0 = fully clean. Both are acceptable.
    code = _run(["lint", CLEAN_WF])
    assert code in (0, 1)


def test_gxwf_roundtrip():
    # exit 1 = benign diffs only; exit 0 = fully clean. Both are acceptable.
    code = _run(["roundtrip", CLEAN_WF])
    assert code in (0, 1)


def test_gxwf_convert_to_format2(tmp_path):
    out = str(tmp_path / "out.gxwf.yml")
    _run(["convert", "--to", "format2", "--output", out, CLEAN_WF], expected_exit=0)
    assert os.path.exists(out)


def test_gxwf_convert_autodetect_to_format2(tmp_path):
    """Auto-detect: .ga input → format2 output."""
    out = str(tmp_path / "out.gxwf.yml")
    _run(["convert", "--output", out, CLEAN_WF], expected_exit=0)
    assert os.path.exists(out)


def test_gxwf_convert_to_native(tmp_path):
    out = str(tmp_path / "out.ga")
    _run(["convert", "--to", "native", "--output", out, FORMAT2_WF], expected_exit=0)
    assert os.path.exists(out)


def test_gxwf_convert_autodetect_to_native(tmp_path):
    """Auto-detect: .gxwf.yml input → native output."""
    out = str(tmp_path / "out.ga")
    _run(["convert", "--output", out, FORMAT2_WF], expected_exit=0)
    assert os.path.exists(out)


def test_gxwf_validate_tree(tmp_path):
    _run(["validate-tree", FIXTURES_DIR])


def test_gxwf_clean_tree(tmp_path):
    _run(["clean-tree", FIXTURES_DIR])


def test_gxwf_lint_tree(tmp_path):
    _run(["lint-tree", FIXTURES_DIR])


def test_gxwf_roundtrip_tree(tmp_path):
    _run(["roundtrip-tree", FIXTURES_DIR])


def test_gxwf_convert_tree_to_format2(tmp_path):
    out_dir = str(tmp_path / "converted")
    os.makedirs(out_dir)
    _run(["convert-tree", "--to", "format2", "--output-dir", out_dir, FIXTURES_DIR], expected_exit=0)


def test_gxwf_convert_tree_to_native(tmp_path):
    # Fixture dir has some files that fail conversion; exit 1 is expected for partial success.
    out_dir = str(tmp_path / "converted")
    os.makedirs(out_dir)
    code = _run(["convert-tree", "--to", "native", "--output-dir", out_dir, FIXTURES_DIR])
    assert code in (0, 1)


def test_gxwf_convert_tree_requires_to(tmp_path):
    """convert-tree must have --to (auto-detect on directories is unreliable)."""
    out_dir = str(tmp_path / "converted")
    os.makedirs(out_dir)
    with pytest.raises(SystemExit) as exc_info:
        main(["convert-tree", "--output-dir", out_dir, FIXTURES_DIR])
    assert exc_info.value.code != 0


def test_gxwf_viz_dispatches_in_process(tmp_path):
    """viz dispatches in-process to gxformat2 cytoscape and writes the graph."""
    out = str(tmp_path / "wf.html")
    _run(["viz", CLEAN_WF, out], expected_exit=0)
    assert os.path.getsize(out) > 0


def test_gxwf_abstract_export_dispatches_in_process(tmp_path):
    """abstract-export dispatches in-process to gxformat2 abstract."""
    out = str(tmp_path / "wf.abstract.cwl")
    _run(["abstract-export", CLEAN_WF, out], expected_exit=0)
    assert os.path.getsize(out) > 0


def test_gxwf_mermaid_dispatches_in_process(tmp_path):
    """mermaid dispatches in-process to gxformat2 mermaid and writes a diagram."""
    out = str(tmp_path / "wf.mmd")
    _run(["mermaid", CLEAN_WF, out], expected_exit=0)
    assert os.path.getsize(out) > 0


def test_gxwf_convert_to_native_compact_warns(capsys):
    """--compact is silently warned when converting to native (has no effect)."""
    _run(["convert", "--to", "native", "--compact", FORMAT2_WF])
    err = capsys.readouterr().err
    assert "no effect" in err
