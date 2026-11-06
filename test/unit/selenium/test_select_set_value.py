"""select_set_value picks the option equal to the value, not the first one containing it."""


def test_select_set_value_picks_the_exact_option(fixture_page):
    page = fixture_page("multiselect.html")
    # "txt" is also a substring of metacyto_clr.txt, which the list shows first.
    page.select_set_value("#extension", "txt")
    assert page.find_element_by_selector("#selected").text == "txt"
