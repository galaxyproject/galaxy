"""Invocation rerun lineage serialization: access filtering and query counts."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    Any,
    cast,
)

import pytest
from sqlalchemy import event

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import WorkflowsManager
from galaxy.schema.fields import Security
from galaxy.schema.invocation import (
    InvocationSerializationParams,
    InvocationSerializationView,
    WorkflowInvocationElementView,
)
from galaxy.webapps.galaxy.services.invocations import InvocationsService

ELEMENT = InvocationSerializationParams(view=InvocationSerializationView.element)


class LineageFixture:
    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        self.app = galaxy_mock.MockApp()
        monkeypatch.setattr(Security, "security", self.app.security, raising=False)
        self.mock_trans = galaxy_mock.MockTrans(app=self.app)
        self.trans = cast(ProvidesUserContext, self.mock_trans)
        self.session = self.app.model.session
        self.owner = self.user("owner")
        self.workflow = model.Workflow()
        self.workflow.stored_workflow = model.StoredWorkflow(user=self.owner, name="workflow")
        self.session.add(self.workflow)
        workflows_manager = WorkflowsManager(cast(Any, self.app), cast(Any, None))
        self.service = InvocationsService(
            self.app.security, cast(Any, None), workflows_manager, cast(Any, None), cast(Any, None)
        )
        self.view_as(self.owner)

    def user(self, name: str) -> model.User:
        user = model.User(email=f"{name}@example.org", password="password", username=name)
        self.session.add(user)
        return user

    def history(self, owner: model.User, importable: bool = False) -> model.History:
        history = model.History(user=owner, name="history")
        history.importable = importable
        self.session.add(history)
        return history

    def invocation(
        self, history: model.History, source: model.WorkflowInvocation | None = None
    ) -> model.WorkflowInvocation:
        invocation = model.WorkflowInvocation()
        invocation.workflow = self.workflow
        invocation.history = history
        invocation.state = model.WorkflowInvocation.states.SCHEDULED
        invocation.rerun_of_invocation = source
        self.session.add(invocation)
        # Flush each invocation so create_time and id order reruns from oldest to newest.
        self.session.flush()
        return invocation

    def view_as(self, user: model.User | None, admin: bool = False) -> None:
        self.mock_trans.set_user(user)
        self.mock_trans.user_is_admin = admin

    def lineage(self, invocation: model.WorkflowInvocation) -> tuple[str | None, str | None]:
        # Serialize from fresh state, as a new request would.
        self.session.flush()
        self.session.expire_all()
        response = self.service.serialize_workflow_invocation(invocation, ELEMENT, trans=self.trans).root
        assert isinstance(response, WorkflowInvocationElementView)
        return response.rerun_of_invocation_id, response.latest_rerun_invocation_id

    def encoded(self, invocation: model.WorkflowInvocation) -> str:
        return str(self.app.security.encode_id(invocation.id))

    @contextmanager
    def count_statements(self) -> Iterator[list[str]]:
        statements: list[str] = []

        def count(_conn, _cursor, statement: str, _parameters, _context, _executemany) -> None:
            statements.append(statement)

        engine = self.app.model.engine
        event.listen(engine, "before_cursor_execute", count)
        try:
            yield statements
        finally:
            event.remove(engine, "before_cursor_execute", count)


@pytest.fixture
def lineage(monkeypatch: pytest.MonkeyPatch) -> LineageFixture:
    return LineageFixture(monkeypatch)


def test_latest_rerun_is_latest_accessible(lineage: LineageFixture) -> None:
    other = lineage.user("other")
    owner_history = lineage.history(lineage.owner)
    source = lineage.invocation(owner_history)
    owner_rerun = lineage.invocation(owner_history, source)
    shared_history = lineage.history(other)
    share = model.HistoryUserShareAssociation(history=shared_history, user=lineage.owner)
    lineage.session.add(share)
    shared_rerun = lineage.invocation(shared_history, source)
    public_rerun = lineage.invocation(lineage.history(other, importable=True), source)
    private_rerun = lineage.invocation(lineage.history(other), source)

    # Owner: the newest rerun is private to another user, the newest accessible one is public.
    assert lineage.lineage(source) == (None, lineage.encoded(public_rerun))
    public_rerun.history.importable = False
    assert lineage.lineage(source) == (None, lineage.encoded(shared_rerun))
    lineage.session.delete(share)
    assert lineage.lineage(source) == (None, lineage.encoded(owner_rerun))
    assert lineage.lineage(owner_rerun) == (lineage.encoded(source), None)

    # The other user can see their own reruns, but not the private source.
    lineage.view_as(other)
    assert lineage.lineage(private_rerun) == (None, None)
    assert lineage.lineage(source)[1] == lineage.encoded(private_rerun)

    # Admins see every link; anonymous users only importable ones.
    lineage.view_as(None, admin=True)
    assert lineage.lineage(source) == (None, lineage.encoded(private_rerun))
    lineage.view_as(None)
    assert lineage.lineage(source) == (None, None)
    owner_history.importable = True
    assert lineage.lineage(owner_rerun) == (lineage.encoded(source), None)


@pytest.mark.parametrize("admin", [False, True])
def test_lineage_query_count_is_independent_of_batch_size_and_fanout(lineage: LineageFixture, admin: bool) -> None:
    history = lineage.history(lineage.owner)
    others = [lineage.user(f"other{i}") for i in range(5)]

    def build_page(size: int) -> list[model.WorkflowInvocation]:
        page = []
        for _ in range(size):
            source = lineage.invocation(history)
            rerun = lineage.invocation(history, source)
            lineage.invocation(history, rerun)
            for other in others:
                lineage.invocation(lineage.history(other), rerun)
            page.append(rerun)
        return page

    small, large = build_page(1), build_page(10)
    lineage.session.commit()
    lineage.view_as(lineage.owner, admin=admin)
    counts = []
    for page in (small, large):
        lineage.session.expire_all()
        page = [lineage.session.get_one(model.WorkflowInvocation, invocation.id) for invocation in page]
        lineage.session.refresh(lineage.owner)  # A request has its user loaded already.
        with lineage.count_statements() as statements:
            resolved = lineage.service._invocation_lineage(lineage.trans, page)
        assert all(len(links) == 2 for links in resolved.values()), resolved
        counts.append(len(statements))
    # One query for the sources and one for the latest reruns, whatever the page size.
    assert counts == [2, 2]
