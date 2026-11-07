import os
import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import cast
from unittest import mock

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.celery.tasks import (
    DISK_USAGE_RUNNING_LOCK,
    DISK_USAGE_WAITING_LOCK,
    recalculate_disk_usage_deduplicated,
)
from galaxy.model import mapping
from galaxy.model.database_utils import DbUrl
from galaxy.model.unittest_utils.model_testing_utils import create_and_drop_database
from galaxy.model.unittest_utils.utils import random_email
from galaxy.objectstore import (
    BaseObjectStore,
    QuotaSourceMap,
)

# GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE='postgresql+psycopg://galaxy@localhost:5432/' pytest test/unit/app/test_disk_usage_recalculation.py
POSTGRES_BASE = os.environ.get("GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE")
pytestmark = pytest.mark.skipif(not POSTGRES_BASE, reason="GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE not set")


class UnlabeledObjectStore:
    def get_quota_source_map(self) -> QuotaSourceMap:
        return QuotaSourceMap()


OBJECT_STORE = cast(BaseObjectStore, UnlabeledObjectStore())


@pytest.fixture(scope="module")
def model_mapping(tmp_path_factory) -> Iterator[mapping.GalaxyModelMapping]:
    url = DbUrl(f"{POSTGRES_BASE}gxtest{uuid.uuid4()}")
    with create_and_drop_database(url):
        model_mapping = mapping.init(str(tmp_path_factory.mktemp("files")), url, create_tables=True)
        try:
            yield model_mapping
        finally:
            model_mapping.session.remove()
            model_mapping.engine.dispose()


@pytest.fixture
def user(model_mapping: mapping.GalaxyModelMapping) -> model.User:
    session = model_mapping.session
    user = model.User(email=random_email(), password="password")
    history = model.History(name="History for deduplicated usage", user=user)
    hda = model.HistoryDatasetAssociation(extension="txt", history=history, create_dataset=True, sa_session=session)
    assert hda.dataset is not None
    hda.dataset.total_size = Decimal(10)
    session.add_all([user, history, hda])
    session.commit()
    return user


def test_recalculates_usage(model_mapping: mapping.GalaxyModelMapping, user: model.User):
    assert recalculate_disk_usage_deduplicated(model_mapping.session(), user, OBJECT_STORE)
    model_mapping.session.refresh(user)
    assert user.disk_usage == 10


def test_skips_while_another_recalculation_is_waiting(model_mapping: mapping.GalaxyModelMapping, user: model.User):
    waiting_lock = {"lock": DISK_USAGE_WAITING_LOCK, "user_id": user.id}
    with model_mapping.engine.connect() as waiting:
        waiting.execute(text("SELECT pg_advisory_lock(:lock, :user_id)"), waiting_lock)
        assert not recalculate_disk_usage_deduplicated(model_mapping.session(), user, OBJECT_STORE)
        waiting.execute(text("SELECT pg_advisory_unlock(:lock, :user_id)"), waiting_lock)
    model_mapping.session.refresh(user)
    assert user.disk_usage is None


def test_recalculates_with_a_single_pooled_connection(model_mapping: mapping.GalaxyModelMapping, user: model.User):
    engine = create_engine(model_mapping.engine.url, pool_size=1, max_overflow=0, pool_timeout=1)
    try:
        with Session(engine) as session:
            pooled_user = session.get(model.User, user.id)
            assert pooled_user
            assert recalculate_disk_usage_deduplicated(session, pooled_user, OBJECT_STORE)
    finally:
        engine.dispose()
    model_mapping.session.refresh(user)
    assert user.disk_usage == 10


def test_wait_for_running_recalculation_times_out(model_mapping: mapping.GalaxyModelMapping, user: model.User):
    with model_mapping.engine.connect() as running:
        running.execute(
            text("SELECT pg_advisory_xact_lock(:lock, :user_id)"),
            {"lock": DISK_USAGE_RUNNING_LOCK, "user_id": user.id},
        )
        with mock.patch("galaxy.celery.tasks.DISK_USAGE_RECALCULATION_WAIT_TIMEOUT", 1):
            with pytest.raises(OperationalError, match="lock timeout"):
                recalculate_disk_usage_deduplicated(model_mapping.session(), user, OBJECT_STORE)
        model_mapping.session.rollback()
        # the waiting slot is free again for the next recalculation
        waiting_lock = {"lock": DISK_USAGE_WAITING_LOCK, "user_id": user.id}
        assert running.scalar(text("SELECT pg_try_advisory_lock(:lock, :user_id)"), waiting_lock)
        running.execute(text("SELECT pg_advisory_unlock(:lock, :user_id)"), waiting_lock)
        running.rollback()
    assert recalculate_disk_usage_deduplicated(model_mapping.session(), user, OBJECT_STORE)
    model_mapping.session.refresh(user)
    assert user.disk_usage == 10


def test_recalculation_runs_under_the_connection_timeouts(model_mapping: mapping.GalaxyModelMapping, user: model.User):
    session = model_mapping.session()
    session.execute(text("SELECT set_config('lock_timeout', '5s', true)"))
    timeouts = []

    def record_timeouts(self, object_store):
        timeouts.append(
            tuple(
                session.execute(
                    text("SELECT current_setting('lock_timeout'), current_setting('statement_timeout')")
                ).one()
            )
        )

    with mock.patch.object(model.User, "calculate_and_set_disk_usage", autospec=True, side_effect=record_timeouts):
        assert recalculate_disk_usage_deduplicated(session, user, OBJECT_STORE)
    session.rollback()
    assert timeouts == [("5s", "0")]
