import pytest

from galaxy import model

# The pagination filters must be applied in SQL, before the page is cut. Seeding
# more items than this proves it: a filter applied to an already-limited page
# would leave the tagged item out of the result entirely.
PAGE_LIMIT = 50
SEEDED_ITEMS = PAGE_LIMIT + 11


@pytest.fixture(scope="module")
def init_model(engine):
    model.mapper_registry.metadata.create_all(engine)


def test_paginated_active_visible_datasets_filters_tag_before_limit(session, make_history):
    history = make_history()
    tagged_hda = _add_hda(session, history, hid=1, name="tagged", tag="genomescope_model")
    for hid in range(2, SEEDED_ITEMS + 1):
        _add_hda(session, history, hid=hid, name=f"untagged-{hid}")
    session.commit()

    rows, total = history.paginated_active_visible_datasets(
        extensions={"txt"},
        valid_states=(model.Dataset.states.OK,),
        tag="genomescope_model",
        limit=PAGE_LIMIT,
    )

    assert total == 1
    assert rows == [tagged_hda]


def test_paginated_active_dataset_collections_filters_tag_before_limit(session, make_history):
    history = make_history()
    tagged_hdca = _add_hdca(session, history, hid=1, name="tagged", tag="genomescope_params")
    for hid in range(2, SEEDED_ITEMS + 1):
        _add_hdca(session, history, hid=hid, name=f"untagged-{hid}")
    session.commit()

    rows, total = history.paginated_active_dataset_collections(
        tag="genomescope_params",
        limit=PAGE_LIMIT,
    )

    assert total == 1
    assert rows == [tagged_hdca]


def test_paginated_active_visible_datasets_multi_tag_match_does_not_shorten_page(session, make_history):
    history = make_history()
    # ``gsm`` matches both of the newer dataset's tag rows.
    newest = _add_hda(session, history, hid=2, name="double-tagged", tag="gsm")
    _append_tag(newest, model.HistoryDatasetAssociationTagAssociation, "gsm", "v1")
    older = _add_hda(session, history, hid=1, name="single-tagged", tag="gsm")
    session.commit()

    rows, total = history.paginated_active_visible_datasets(tag="gsm", limit=2)

    assert total == 2
    assert rows == [newest, older]


def test_paginated_active_dataset_collections_multi_tag_match_does_not_shorten_page(session, make_history):
    history = make_history()
    newest = _add_hdca(session, history, hid=2, name="double-tagged", tag="gsp")
    _append_tag(newest, model.HistoryDatasetCollectionTagAssociation, "gsp", "v1")
    older = _add_hdca(session, history, hid=1, name="single-tagged", tag="gsp")
    session.commit()

    rows, total = history.paginated_active_dataset_collections(tag="gsp", limit=2)

    assert total == 2
    assert rows == [newest, older]


def test_paginated_active_visible_datasets_tag_eq_matches_name_with_any_value(session, make_history):
    history = make_history()
    valueless = _add_hda(session, history, hid=1, name="valueless", tag="gsm")
    valued = _add_hda(session, history, hid=2, name="valued", tag="gsm", tag_value="v1")
    _add_hda(session, history, hid=3, name="other", tag="unrelated")
    session.commit()

    rows, total = history.paginated_active_visible_datasets(tag="gsm", limit=PAGE_LIMIT)

    assert total == 2
    assert rows == [valued, valueless]


def test_paginated_active_visible_datasets_tag_eq_with_value_matches_that_value_only(session, make_history):
    history = make_history()
    _add_hda(session, history, hid=1, name="valueless", tag="gsm")
    valued = _add_hda(session, history, hid=2, name="valued", tag="gsm", tag_value="v1")
    session.commit()

    rows, total = history.paginated_active_visible_datasets(tag="gsm:v1", limit=PAGE_LIMIT)

    assert total == 1
    assert rows == [valued]


def _append_tag(item, tag_association_class, name, value):
    item.tags.append(tag_association_class(user_tname=name, user_value=value, value=value))


def _add_hda(session, history, *, hid, name, tag=None, tag_value=None):
    dataset = model.Dataset(state=model.Dataset.states.OK)
    hda = model.HistoryDatasetAssociation(
        dataset=dataset,
        history=history,
        hid=hid,
        name=name,
        extension="txt",
        visible=True,
        deleted=False,
    )
    if tag:
        _append_tag(hda, model.HistoryDatasetAssociationTagAssociation, tag, tag_value)
    session.add(hda)
    return hda


def _add_hdca(session, history, *, hid, name, tag=None, tag_value=None):
    hdca = model.HistoryDatasetCollectionAssociation(
        collection=model.DatasetCollection(collection_type="list"),
        history=history,
        hid=hid,
        name=name,
        visible=True,
        deleted=False,
    )
    if tag:
        _append_tag(hdca, model.HistoryDatasetCollectionTagAssociation, tag, tag_value)
    session.add(hdca)
    return hdca
