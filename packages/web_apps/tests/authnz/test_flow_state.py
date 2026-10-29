import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import (
    create_engine,
    event,
    select,
)
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.authnz.flow_state import (
    authentication_id,
    FlowState,
    InvalidFlow,
)


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    database_url = os.environ.get("GALAXY_TEST_OIDC_DATABASE_URL")
    engine = create_engine(database_url or f"sqlite:///{tmp_path_factory.mktemp('flow') / 'flow.sqlite'}")
    model.mapper_registry.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def flow(engine):
    with Session(engine) as session:
        browser = model.GalaxySession(is_valid=True)
        session.add(browser)
        session.commit()
        yield FlowState(session, browser, "keycloak")


def test_persistence_binding_and_replay(flow, engine):
    identifier = flow.save("confirmation", {"uid": "trusted"})
    browser_id = flow.galaxy_session.id
    with Session(engine) as other:
        browser = other.get(model.GalaxySession, browser_id)
        with pytest.raises(InvalidFlow):
            FlowState(other, browser, "google").consume("confirmation", identifier)
        other_browser = model.GalaxySession(is_valid=True)
        other.add(other_browser)
        other.commit()
        with pytest.raises(InvalidFlow):
            FlowState(other, other_browser, "keycloak").consume("confirmation", identifier)
        original = FlowState(other, browser, "keycloak")
        with pytest.raises(InvalidFlow):
            original.consume("authentication", identifier)
        assert original.consume("confirmation", identifier) == {"uid": "trusted"}
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", identifier)


def test_replacement_and_expiry(flow, monkeypatch):
    monkeypatch.setattr("galaxy.authnz.flow_state.time.time", lambda: 1000)
    obsolete = flow.save("confirmation", {})
    current = flow.save("confirmation", {})
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", obsolete)
    monkeypatch.setattr("galaxy.authnz.flow_state.time.time", lambda: 1600)
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", current)
    with pytest.raises(InvalidFlow):
        flow.save("confirmation", {}, expires_at=1599)


@pytest.mark.parametrize("identifier", [None, "", "a" * 31, "a" * 33, "G" * 32, {"id_token": "forged"}])
def test_invalid_identifier(identifier):
    with pytest.raises(InvalidFlow):
        FlowState._validate_identifier(identifier)


@pytest.mark.parametrize(
    "field,value",
    [("provider", "google"), ("session_id", -1), ("version", 2), ("payload", []), ("expires_at", float("nan"))],
)
def test_corrupt_envelope(flow, field, value):
    identifier = flow.save("confirmation", {})
    row = flow.session.scalars(select(model.PSAPartial).where(model.PSAPartial.token == identifier)).one()
    data = json.loads(row.data)
    data[field] = value
    row.data = json.dumps(data)
    flow.session.commit()
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", identifier)


def test_cleanup_does_not_touch_psa_partials(flow, monkeypatch):
    monkeypatch.setattr("galaxy.authnz.flow_state.time.time", lambda: 1000)
    obsolete = flow.save("confirmation", {})
    normal = model.PSAPartial("ordinary-partial", "{}", 4, "keycloak")
    flow.session.add(normal)
    flow.session.commit()
    normal_id = normal.id
    monkeypatch.setattr("galaxy.authnz.flow_state.time.time", lambda: 1601)
    identifier = flow.save("confirmation", {})
    assert flow.session.scalars(select(model.PSAPartial).where(model.PSAPartial.token == obsolete)).first() is None
    assert flow.session.get(model.PSAPartial, normal_id) is not None
    monkeypatch.setattr(model.PSAPartial, "sa_session", flow.session)
    assert model.PSAPartial.load(identifier) is None
    assert model.PSAPartial.load("ordinary-partial") is not None


def test_ambiguous_identifier_is_rejected(flow):
    identifier = flow.save("confirmation", {})
    row = flow.session.scalars(select(model.PSAPartial).where(model.PSAPartial.token == identifier)).one()
    flow.session.add(model.PSAPartial(row.token, row.data, row.next_step, row.backend))
    flow.session.commit()
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", identifier)


def test_concurrent_consumption(flow, engine):
    identifier = flow.save("confirmation", {"uid": "trusted"})
    browser_id = flow.galaxy_session.id
    barrier = threading.Barrier(2)

    def consume():
        with Session(engine) as session:
            browser = session.get(model.GalaxySession, browser_id)
            state = FlowState(session, browser, "keycloak")

            def before_execute(execute_state):
                if execute_state.is_delete:
                    barrier.wait(timeout=10)

            event.listen(session, "do_orm_execute", before_execute)
            try:
                return state.consume("confirmation", identifier)
            except InvalidFlow:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert results.count({"uid": "trusted"}) == 1
    assert results.count(None) == 1


def test_authentication_id():
    assert len(authentication_id("state")) == 32
    assert authentication_id("state") != authentication_id("another-state")
    for invalid in (None, "", "a" * 1025):
        with pytest.raises(InvalidFlow):
            authentication_id(invalid)


@pytest.mark.parametrize("expiry", [float("nan"), float("inf"), "tomorrow"])
def test_invalid_expiration_is_not_replaced_with_default(flow, expiry):
    with pytest.raises(InvalidFlow):
        flow.save("confirmation", {}, expires_at=expiry)


def test_session_invalidated_by_another_request(flow, engine):
    identifier = flow.save("confirmation", {})
    browser_id = flow.galaxy_session.id
    # Cache the still-valid session in the first request.
    assert flow.galaxy_session.is_valid
    with Session(engine) as other:
        browser = other.get(model.GalaxySession, browser_id)
        assert browser is not None
        browser.is_valid = False
        other.commit()
    with pytest.raises(InvalidFlow):
        flow.consume("confirmation", identifier)
