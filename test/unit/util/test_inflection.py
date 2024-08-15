import pytest

from galaxy.util.inflection import Inflector

SINGULAR_TO_PLURAL = {
    "search": "searches",
    "switch": "switches",
    "fix": "fixes",
    "box": "boxes",
    "process": "processes",
    "address": "addresses",
    "case": "cases",
    "stack": "stacks",
    "wish": "wishes",
    "category": "categories",
    "query": "queries",
    "ability": "abilities",
    "agency": "agencies",
    "movie": "movies",
    "archive": "archives",
    "index": "indices",
    "wife": "wives",
    "half": "halves",
    "move": "moves",
    "salesperson": "salespeople",
    "person": "people",
    "spokesman": "spokesmen",
    "man": "men",
    "woman": "women",
    "basis": "bases",
    "diagnosis": "diagnoses",
    "datum": "data",
    "medium": "media",
    "analysis": "analyses",
    "node_child": "node_children",
    "child": "children",
    "experience": "experiences",
    "day": "days",
    "comment": "comments",
    "foobar": "foobars",
    "newsletter": "newsletters",
    "old_news": "old_news",
    "news": "news",
    "series": "series",
    "species": "species",
    "subspecies": "subspecies",
    "quiz": "quizzes",
    "perspective": "perspectives",
    "ox": "oxen",
    "photo": "photos",
    "buffalo": "buffaloes",
    "tomato": "tomatoes",
    "information": "information",
    "misinformation": "misinformation",
    "equipment": "equipment",
    "bus": "buses",
    "status": "statuses",
    "mouse": "mice",
    "louse": "lice",
    "house": "houses",
    "octopus": "octopi",
    "virus": "viruses",
    "alias": "aliases",
    "portfolio": "portfolios",
    "vertex": "vertices",
    "matrix": "matrices",
    "axis": "axes",
    "testis": "testes",
    "crisis": "crises",
    "rice": "rice",
    "shoe": "shoes",
    "horse": "horses",
    "prize": "prizes",
    "edge": "edges",
}


@pytest.fixture
def inflector():
    return Inflector()


@pytest.mark.parametrize("test_data", SINGULAR_TO_PLURAL.items())
def test_pluralize_rules(test_data, inflector):
    assert test_data[1] == inflector.pluralize(test_data[0])


@pytest.mark.parametrize("test_data", SINGULAR_TO_PLURAL.items())
def test_singularize_rules(test_data, inflector):
    assert test_data[0] == inflector.singularize(test_data[1])


def test_cond_plural(inflector):
    assert "edge" == inflector.cond_plural(1, "edge")
    assert "edges" == inflector.cond_plural(-1, "edge")
    assert "edges" == inflector.cond_plural(0, "edge")
    assert "edges" == inflector.cond_plural(2, "edge")
