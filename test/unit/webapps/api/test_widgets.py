import os
import re

import pytest
from jsonschema import (
    Draft202012Validator,
    ValidationError,
)

from galaxy.util import galaxy_directory
from galaxy.webapps.galaxy.api.widgets import WIDGETS

WIDGET_ROUTES = os.path.join(galaxy_directory(), "client", "src", "entry", "widgets", "routes.ts")


def widget(widget_id: str):
    return next(w for w in WIDGETS if w.id == widget_id)


def client_paths() -> dict[str, str]:
    """Each named client route as a path template, e.g. `histories/{history_id}/graph`."""
    with open(WIDGET_ROUTES) as fh:
        routes = re.findall(r'name: "(\w+)",\s*path: `/widgets/([^`]+)`', fh.read())
    return {name: re.sub(r":(\w+)\([^)]*\)", r"{\1}", path) for name, path in routes}


@pytest.mark.parametrize("entry", WIDGETS, ids=lambda w: w.id)
def test_client_serves_each_widget_at_its_path(entry):
    assert client_paths().get(entry.id) == entry.path


@pytest.mark.parametrize("entry", WIDGETS, ids=lambda w: w.id)
def test_path_parameters_are_required(entry):
    Draft202012Validator.check_schema(entry.parameters_schema)
    for name in re.findall(r"{(\w+)}", entry.path):
        assert name in entry.parameters_schema["required"]


@pytest.mark.parametrize(
    "parameters",
    [
        {"history_id": "1a"},
        {"history_id": "1a", "seed_src": "hda", "seed_id": "2b"},
        {"history_id": "1a", "seed_src": "tool_request", "seed_id": "2b"},
    ],
)
def test_history_graph_accepts(parameters):
    Draft202012Validator(widget("history_graph").parameters_schema).validate(parameters)


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"history_id": "not-hex"},
        {"history_id": "1a", "seed_src": "hda"},
        {"history_id": "1a", "seed_id": "2b"},
        {"history_id": "1a", "seed_src": "job", "seed_id": "2b"},
        {"history_id": "1a", "unknown": "x"},
    ],
)
def test_history_graph_rejects(parameters):
    with pytest.raises(ValidationError):
        Draft202012Validator(widget("history_graph").parameters_schema).validate(parameters)


@pytest.mark.parametrize("parameters", [{"page_id": "1a"}, {"page_id": "1a", "heading": False}])
def test_page_accepts(parameters):
    Draft202012Validator(widget("page").parameters_schema).validate(parameters)


@pytest.mark.parametrize(
    "parameters",
    [{}, {"page_id": "not-hex"}, {"page_id": "1a", "displayOnly": True}, {"page_id": "1a", "embed": True}],
)
def test_page_rejects(parameters):
    with pytest.raises(ValidationError):
        Draft202012Validator(widget("page").parameters_schema).validate(parameters)


@pytest.mark.parametrize(
    "parameters",
    [
        {"workflow_id": "1a"},
        {
            "workflow_id": "1a",
            "version": 2,
            "zoom": 0.5,
            "buttons": True,
            "about": False,
            "heading": False,
            "minimap": True,
            "zoom_controls": True,
            "initialX": -20,
            "initialY": -20,
        },
    ],
)
def test_workflow_accepts(parameters):
    Draft202012Validator(widget("workflow").parameters_schema).validate(parameters)


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"workflow_id": "not-hex"},
        {"workflow_id": "1a", "zoom": "large"},
        {"workflow_id": "1a", "initial_x": 1},
        {"workflow_id": "1a", "embed": True},
    ],
)
def test_workflow_rejects(parameters):
    with pytest.raises(ValidationError):
        Draft202012Validator(widget("workflow").parameters_schema).validate(parameters)
