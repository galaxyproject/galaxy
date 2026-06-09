"""format2 emitter quotes scalars a YAML 1.1 reader would otherwise coerce.

Galaxy tool_state stores select/boolean option values such as ``"no"`` as strings.
PyYAML (YAML 1.1) coerces bare ``no``/``yes``/``on``/``off`` to bools, so the emitter
must quote them; a quoted scalar reads back as the string under both 1.1 and 1.2.
"""

import tempfile

from galaxy.tool_util.workflow_state.export_format2 import format_yaml
from galaxy.tool_util.workflow_state.workflow_tools import load_workflow


def _write_yml(text: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".gxwf.yml", delete=False) as f:
        f.write(text)
        return f.name


def test_format_yaml_quotes_reserved_word_strings():
    out = format_yaml({"use_guide": "no", "label": "hello", "count": 5, "enabled": False})
    assert "use_guide: 'no'" in out
    assert "label: hello" in out
    assert "count: 5" in out
    assert "enabled: false" in out


def test_format_yaml_quotes_numeric_strings():
    out = format_yaml({"fraction": "0.01"})
    assert "fraction: '0.01'" in out


def test_emitted_reserved_words_round_trip_through_reader():
    out = format_yaml({"steps": {"s": {"tool_state": {"use_guide": "no"}}}})
    path = _write_yml(out)
    reloaded = load_workflow(path)["steps"]["s"]["tool_state"]["use_guide"]
    assert reloaded == "no"
