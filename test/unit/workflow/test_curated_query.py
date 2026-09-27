"""Unit tests for ``WorkflowsManager.curated_index_query``.

These run against a real Galaxy model schema in an in-memory SQLite database
(via ``MockTrans``), because the behaviour under test lives entirely in the SQL
-- exact-match owner filtering, visibility, ordering and pagination -- and a
mocked session would prove nothing about any of it.
"""

from datetime import datetime
from typing import (
    Any,
    cast,
)

import pytest

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import WorkflowsManager
from galaxy.schema.schema import CuratedWorkflowsQueryPayload

CURATED_OWNER = "iwc"


@pytest.fixture
def trans() -> MockTrans:
    return MockTrans()


@pytest.fixture
def manager(trans: MockTrans) -> WorkflowsManager:
    return WorkflowsManager(trans.app)


def make_user(trans: MockTrans, username: str, deleted: bool = False) -> model.User:
    user = model.User(email=f"{username}@example.com", password="password", username=username)
    user.deleted = deleted
    trans.sa_session.add(user)
    trans.sa_session.commit()
    return user


def make_workflow(
    trans: MockTrans,
    user: model.User,
    name: str,
    published: bool = True,
    deleted: bool = False,
    hidden: bool = False,
    update_time: datetime | None = None,
    tags: list[str] | None = None,
) -> model.StoredWorkflow:
    stored_workflow = model.StoredWorkflow()
    stored_workflow.user = user
    stored_workflow.name = name
    stored_workflow.published = published
    stored_workflow.deleted = deleted
    stored_workflow.hidden = hidden
    workflow = model.Workflow()
    workflow.stored_workflow = stored_workflow
    stored_workflow.latest_workflow = workflow
    for tag in tags or []:
        association = model.StoredWorkflowTagAssociation()
        association.user_tname = tag
        association.user = user
        stored_workflow.tags.append(association)
    trans.sa_session.add(stored_workflow)
    trans.sa_session.commit()
    if update_time is not None:
        # Assigned after the insert so it is not overwritten by the column
        # default, and committed on its own so ``onupdate`` does not fire.
        stored_workflow.update_time = update_time
        trans.sa_session.commit()
    return stored_workflow


def query_rows(manager: WorkflowsManager, trans: MockTrans, owners: list[str], **payload_kwds: Any):
    payload = CuratedWorkflowsQueryPayload(**payload_kwds)
    # MockTrans supplies everything the query touches without being a ProvidesUserContext.
    return manager.curated_index_query(cast(ProvidesUserContext, trans), payload, owners)


def query(manager: WorkflowsManager, trans: MockTrans, owners: list[str], **payload_kwds: Any):
    rows, total_matches = query_rows(manager, trans, owners, **payload_kwds)
    return [row.name for row in rows], total_matches


def test_owner_match_is_exact_and_case_insensitive(manager: WorkflowsManager, trans: MockTrans) -> None:
    """An allowlist of ``iwc`` must not hand the curated tab to ``iwc-mirror``."""
    owner = make_user(trans, CURATED_OWNER)
    mirror = make_user(trans, f"{CURATED_OWNER}-mirror")
    prefixed = make_user(trans, f"not-{CURATED_OWNER}")
    make_workflow(trans, owner, "Curated")
    make_workflow(trans, mirror, "Impersonator")
    make_workflow(trans, prefixed, "Also Not Curated")

    names, total_matches = query(manager, trans, [CURATED_OWNER])
    assert names == ["Curated"]
    assert total_matches == 1

    # The config value is compared case-insensitively, so a differently-cased
    # entry selects the same account and still only that account.
    names, total_matches = query(manager, trans, ["IWC"])
    assert names == ["Curated"]
    assert total_matches == 1


def test_empty_owner_list_matches_nothing(manager: WorkflowsManager, trans: MockTrans) -> None:
    make_workflow(trans, make_user(trans, CURATED_OWNER), "Curated")
    assert query(manager, trans, []) == ([], 0)


def test_multiple_owners_are_all_included(manager: WorkflowsManager, trans: MockTrans) -> None:
    make_workflow(trans, make_user(trans, CURATED_OWNER), "From IWC")
    make_workflow(trans, make_user(trans, "usegalaxy"), "From usegalaxy")
    make_workflow(trans, make_user(trans, "someone-else"), "From someone else")

    names, total_matches = query(manager, trans, [CURATED_OWNER, "usegalaxy"])
    assert sorted(names) == ["From IWC", "From usegalaxy"]
    assert total_matches == 2


def test_unpublished_deleted_and_hidden_workflows_are_excluded(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    make_workflow(trans, owner, "Visible")
    make_workflow(trans, owner, "Unpublished", published=False)
    make_workflow(trans, owner, "Deleted", deleted=True)
    make_workflow(trans, owner, "Hidden", hidden=True)

    names, total_matches = query(manager, trans, [CURATED_OWNER])
    assert names == ["Visible"]
    assert total_matches == 1


def test_workflows_owned_by_a_deleted_user_are_excluded(manager: WorkflowsManager, trans: MockTrans) -> None:
    make_workflow(trans, make_user(trans, CURATED_OWNER, deleted=True), "Orphaned")
    assert query(manager, trans, [CURATED_OWNER]) == ([], 0)


def test_default_ordering_is_most_recently_updated_first(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    make_workflow(trans, owner, "Oldest", update_time=datetime(2023, 1, 1))
    make_workflow(trans, owner, "Newest", update_time=datetime(2025, 1, 1))
    make_workflow(trans, owner, "Middle", update_time=datetime(2024, 1, 1))

    names, _ = query(manager, trans, [CURATED_OWNER])
    assert names == ["Newest", "Middle", "Oldest"]


def test_sort_by_name_honours_sort_desc(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    for name in ("Bravo", "Alpha", "Charlie"):
        make_workflow(trans, owner, name)

    names, _ = query(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=False)
    assert names == ["Alpha", "Bravo", "Charlie"]

    names, _ = query(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=True)
    assert names == ["Charlie", "Bravo", "Alpha"]


def test_sort_by_name_ignores_case(manager: WorkflowsManager, trans: MockTrans) -> None:
    """Raw collation puts every capitalised name first under SQLite; the catalog lowercases."""
    owner = make_user(trans, CURATED_OWNER)
    for name in ("charlie", "Beta", "alpha"):
        make_workflow(trans, owner, name)

    names, _ = query(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=False)
    assert names == ["alpha", "Beta", "charlie"]

    names, _ = query(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=True)
    assert names == ["charlie", "Beta", "alpha"]


def test_tied_names_break_ties_in_the_sort_direction(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    first = make_workflow(trans, owner, "Same name")
    second = make_workflow(trans, owner, "Same name")
    rows, _ = query_rows(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=False)
    assert [row.id for row in rows] == [first.id, second.id]

    rows, _ = query_rows(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=True)
    assert [row.id for row in rows] == [second.id, first.id]


def test_pagination_reports_the_pre_limit_total(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    for name in ("Alpha", "Bravo", "Charlie", "Delta", "Echo"):
        make_workflow(trans, owner, name)

    first_page, total_matches = query(manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=False, limit=2)
    assert first_page == ["Alpha", "Bravo"]
    assert total_matches == 5

    last_page, total_matches = query(
        manager, trans, [CURATED_OWNER], sort_by="name", sort_desc=False, limit=2, offset=4
    )
    assert last_page == ["Echo"]
    assert total_matches == 5


def test_search_filters_by_name_term(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    make_workflow(trans, owner, "Variant calling")
    make_workflow(trans, owner, "RNA-seq counts")

    names, total_matches = query(manager, trans, [CURATED_OWNER], search="name:variant")
    assert names == ["Variant calling"]
    assert total_matches == 1


def test_search_filters_by_tag_term(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    make_workflow(trans, owner, "Tagged", tags=["transcriptomics"])
    make_workflow(trans, owner, "Untagged")

    names, total_matches = query(manager, trans, [CURATED_OWNER], search="tag:transcriptomics")
    assert names == ["Tagged"]
    assert total_matches == 1


def test_raw_text_search_matches_name_or_tag(manager: WorkflowsManager, trans: MockTrans) -> None:
    owner = make_user(trans, CURATED_OWNER)
    make_workflow(trans, owner, "Matched by name: genomics")
    make_workflow(trans, owner, "Matched by tag", tags=["genomics"])
    make_workflow(trans, owner, "Not matched at all")

    names, total_matches = query(manager, trans, [CURATED_OWNER], search="genomics")
    assert sorted(names) == ["Matched by name: genomics", "Matched by tag"]
    assert total_matches == 2


def test_search_never_leaks_workflows_from_other_owners(manager: WorkflowsManager, trans: MockTrans) -> None:
    make_workflow(trans, make_user(trans, CURATED_OWNER), "Shared name")
    make_workflow(trans, make_user(trans, f"{CURATED_OWNER}-mirror"), "Shared name")

    names, total_matches = query(manager, trans, [CURATED_OWNER], search="shared")
    assert names == ["Shared name"]
    assert total_matches == 1


def test_search_with_thousands_of_keyed_terms_is_bounded(manager: WorkflowsManager, trans: MockTrans) -> None:
    """Uncapped, each ``name:`` term is its own predicate and SQLite rejects the tree."""
    make_workflow(trans, make_user(trans, CURATED_OWNER), "x marks the spot")

    names, total_matches = query(manager, trans, [CURATED_OWNER], search=" ".join("name:x" for _ in range(1100)))
    assert names == ["x marks the spot"]
    assert total_matches == 1
