"""tool_form_fill adds repeat instances inside collapsed sections and enclosing repeat instances."""

import pytest


def _value(page, path):
    return page.components.tool_form.parameter_text_input(parameter=path).wait_for_value()


def test_tool_form_fill_inside_a_repeat_instance(fixture_page):
    page = fixture_page("nested_repeat.html")
    page.tool_form_fill(values={"outer_1|inner_2|x": "deep"})
    assert _value(page, "outer_1|inner_2|x") == "deep"
    parameter_div = page.components.tool_form.parameter_div
    # Only the instances the path needs: two outer, three inner in outer_1, outer_0's one untouched.
    for path in ("outer_2|inner_0|x", "outer_1|inner_3|x", "outer_0|inner_1|x"):
        parameter_div(parameter=path).assert_absent()


def test_tool_form_fill_expands_a_section_an_added_instance_holds(fixture_page):
    page = fixture_page("nested_repeat.html")
    page.tool_form_fill(values={"wrap_0|sec|inner_1|x": "v"})
    assert _value(page, "wrap_0|sec|inner_1|x") == "v"


def test_tool_form_fill_counts_instances_holding_no_field(fixture_page):
    page = fixture_page("nested_repeat.html")
    page.tool_form_fill(values={"bare_1|inner_0|x": "v"})
    assert _value(page, "bare_1|inner_0|x") == "v"
    page.components.tool_form.parameter_div(parameter="bare_2|inner_0|x").assert_absent()


def test_tool_form_fill_refuses_same_named_repeats_in_one_scope(fixture_page):
    page = fixture_page("nested_repeat.html")
    with pytest.raises(ValueError, match="2 repeat insert buttons match a\\|dup"):
        page.tool_form_fill(values={"a|dup_0|x": "v"})


def test_tool_form_fill_in_a_collapsed_section_keeps_open_sections_open(fixture_page):
    page = fixture_page("sections.html")
    page.tool_form_fill(values={"sec|queries_1|x": "v"})
    assert _value(page, "sec|queries_1|x") == "v"
    page.components.tool_form.parameter_div(parameter="sec|queries_2|x").assert_absent()
    assert not page.components.tool_form.section_header_collapsed.all()
    # Clicking a header toggles it, so the expanded "open" must stay open while its nested section opens.
    assert page.find_element_by_selector("#open > .portlet-content").is_displayed()
    assert page.find_element_by_selector("#inner_sec > .portlet-content").is_displayed()
