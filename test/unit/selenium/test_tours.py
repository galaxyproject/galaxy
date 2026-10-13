"""Tour loading shared by Galaxy's tour registry and the browser automation."""

from galaxy.navigation.tours import (
    get_tour_id_from_path,
    load_tour_from_path,
)

TOUR = """
name: Example Tour
description: Walks the example.
title_default: Example Tour Step
steps:
    - content: "Welcome to <b>Galaxy</b>."
    - title: "Open the Upload Activity"
      component: upload_activity.activity
      intro: "Use this button."
      position: right
"""


def _write_tour(tmp_path):
    path = tmp_path / "example.tour.yaml"
    path.write_text(TOUR)
    return path


def test_tour_id_is_the_file_name_without_extension(tmp_path):
    assert get_tour_id_from_path(_write_tour(tmp_path)) == "example.tour"


def test_steps_are_normalized_for_the_client(tmp_path):
    tour = load_tour_from_path(_write_tour(tmp_path))
    first, second = tour["steps"]
    assert tour["requirements"] == []
    assert first["title"] == "Example Tour Step"
    assert first["orphan"] is True
    assert second["content"] == "Use this button."
    assert "intro" not in second
    assert second["placement"] == "right"
    assert "component" not in second
    assert second["element"]


def test_components_can_be_left_for_the_caller_to_resolve(tmp_path):
    tour = load_tour_from_path(_write_tour(tmp_path), resolve_components=False)
    second = tour["steps"][1]
    assert second["component"] == "upload_activity.activity"
    assert second["content"] == "Use this button."
    assert "element" not in second
