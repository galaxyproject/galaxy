import time
from unittest import mock

import pytest
import sqlalchemy
from sqlalchemy import (
    false,
    select,
    true,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.app_unittest_utils.galaxy_mock import mock_url_builder
from galaxy.managers import (
    base,
    hdas,
)
from galaxy.managers.histories import (
    HistoryDeserializer,
    HistoryFilters,
    HistoryManager,
    HistorySerializer,
)
from galaxy.model.base import transaction
from .base import BaseTestCase

default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)
user4_data = dict(email="user4@user4.user4", username="user4", password=default_password)
parsed_filter = base.ModelFilterParser.parsed_filter


class TestHistoryManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.hda_manager = self.app[hdas.HDAManager]

    def add_hda_to_history(self, history, **kwargs):
        dataset = self.hda_manager.dataset_manager.create()
        hda = self.hda_manager.create(history=history, dataset=dataset, **kwargs)
        return hda

    def test_base(self):
        user2 = self.user_manager.create(**user2_data)
        user3 = self.user_manager.create(**user3_data)

        self.log("should be able to create a new history")
        history1 = self.history_manager.create(name="history1", user=user2)
        assert isinstance(history1, model.History)
        assert history1.name == "history1"
        assert history1.user == user2
        assert history1 == self.trans.sa_session.get(model.History, history1.id)
        assert (
            history1
            == self.trans.sa_session.execute(
                select(model.History).filter(model.History.name == "history1")
            ).scalar_one()
        )
        assert (
            history1
            == self.trans.sa_session.execute(select(model.History).filter(model.History.user == user2)).scalar_one()
        )

        history2 = history1.copy(target_user=user3)

        self.log("should be able to query")
        histories = self.trans.sa_session.scalars(select(model.History)).all()
        assert self.history_manager.one(filters=(model.History.id == history1.id)) == history1
        assert self.history_manager.list() == histories
        assert self.history_manager.by_id(history1.id) == history1
        assert self.history_manager.by_ids([history2.id, history1.id]) == [history2, history1]

        self.log("should be able to limit and offset")
        assert self.history_manager.list(limit=1) == histories[0:1]
        assert self.history_manager.list(offset=1) == histories[1:]
        assert self.history_manager.list(limit=1, offset=1) == histories[1:2]

        assert self.history_manager.list(limit=0) == []
        assert self.history_manager.list(offset=3) == []

        self.log("should be able to order")
        history3 = self.history_manager.create(name="history3", user=user2)
        name_first_then_time = (
            model.History.name,
            sqlalchemy.desc(model.History.create_time),
        )
        assert self.history_manager.list(order_by=name_first_then_time) == [history2, history1, history3]

    def test_copy(self):
        user2 = self.user_manager.create(**user2_data)
        user3 = self.user_manager.create(**user3_data)

        self.log("should be able to copy a history (and it's hdas)")
        history1 = self.history_manager.create(name="history1", user=user2)
        tags = ["tag-one"]
        annotation = "history annotation"
        self.history_manager.tag_handler.set_tags_from_list(user=user2, item=history1, new_tags_list=tags)
        self.history_manager.annotate(history1, annotation, user=user2)

        hda = self.add_hda_to_history(history1, name="wat")
        hda_tags = ["tag-one", "tag-two"]
        hda_annotation = "annotation"
        self.app.tag_handler.set_tags_from_list(user=user2, item=hda, new_tags_list=hda_tags)
        self.hda_manager.annotate(hda, hda_annotation, user=user2)

        history2 = history1.copy(target_user=user3)
        assert isinstance(history2, model.History)
        assert history2.user == user3
        assert history2 == self.trans.sa_session.get(model.History, history2.id)
        assert history2.name == history1.name
        assert history2 != history1

        copied_hda = history2.datasets[0]
        assert hda.make_tag_string_list() == copied_hda.make_tag_string_list()
        copied_hda_annotation = self.hda_manager.annotation(copied_hda)
        assert hda_annotation == copied_hda_annotation

    def test_has_user(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        item1 = self.history_manager.create(user=owner)
        item2 = self.history_manager.create(user=owner)
        self.history_manager.create(user=non_owner)

        self.log("should be able to list items by user")
        user_histories = self.history_manager.by_user(owner)
        assert user_histories == [item1, item2]

    def test_ownable(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        item1 = self.history_manager.create(user=owner)

        self.log("should be able to poll whether a given user owns an item")
        assert self.history_manager.is_owner(item1, owner)
        assert not self.history_manager.is_owner(item1, non_owner)

        self.log("should raise an error when checking ownership with non-owner")
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.history_manager.error_unless_owner(item1, non_owner)
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.history_manager.get_owned(item1.id, non_owner)

        self.log("should not raise an error when checking ownership with owner")
        assert self.history_manager.error_unless_owner(item1, owner) == item1
        assert self.history_manager.get_owned(item1.id, owner) == item1

        self.log("should not raise an error when checking ownership with admin")
        assert self.history_manager.is_owner(item1, self.admin_user)
        assert self.history_manager.error_unless_owner(item1, self.admin_user) == item1
        assert self.history_manager.get_owned(item1.id, self.admin_user) == item1

    def test_accessible(self):
        owner = self.user_manager.create(**user2_data)
        item1 = self.history_manager.create(user=owner)

        non_owner = self.user_manager.create(**user3_data)

        self.log("should be inaccessible by default except to owner")
        assert self.history_manager.is_accessible(item1, owner)
        assert self.history_manager.is_accessible(item1, self.admin_user)
        assert not self.history_manager.is_accessible(item1, non_owner)

        self.log("should raise an error when checking accessibility with non-owner")
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.history_manager.error_unless_accessible(item1, non_owner)
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.history_manager.get_accessible(item1.id, non_owner)

        self.log("should not raise an error when checking ownership with owner")
        assert self.history_manager.error_unless_accessible(item1, owner) == item1
        assert self.history_manager.get_accessible(item1.id, owner) == item1

        self.log("should not raise an error when checking ownership with admin")
        assert self.history_manager.is_accessible(item1, self.admin_user)
        assert self.history_manager.error_unless_accessible(item1, self.admin_user) == item1
        assert self.history_manager.get_accessible(item1.id, self.admin_user) == item1

    def test_importable(self):
        owner = self.user_manager.create(**user2_data)
        self.trans.set_user(owner)
        non_owner = self.user_manager.create(**user3_data)

        item1 = self.history_manager.create(user=owner)

        self.log("should not be importable by default")
        assert not item1.importable
        assert item1.slug is None

        self.log("should be able to make importable (accessible by link) to all users")
        accessible = self.history_manager.make_importable(item1)
        assert accessible == item1
        assert accessible.slug is not None
        assert accessible.importable

        for user in self.user_manager.list():
            assert self.history_manager.is_accessible(accessible, user)

        self.log("should be able to make non-importable/inaccessible again")
        inaccessible = self.history_manager.make_non_importable(accessible)
        assert inaccessible == accessible
        assert inaccessible.slug is not None
        assert not inaccessible.importable

        assert self.history_manager.is_accessible(inaccessible, owner)
        assert not self.history_manager.is_accessible(inaccessible, non_owner)
        assert self.history_manager.is_accessible(inaccessible, self.admin_user)

    def test_published(self):
        owner = self.user_manager.create(**user2_data)
        self.trans.set_user(owner)
        non_owner = self.user_manager.create(**user3_data)

        item1 = self.history_manager.create(user=owner)

        self.log("should not be published by default")
        assert not item1.published
        assert item1.slug is None

        self.log("should be able to publish (listed publicly) to all users")
        published = self.history_manager.publish(item1)
        assert published == item1
        assert published.published
        # note: publishing sets importable to true as well
        assert published.importable
        assert published.slug is not None

        for user in self.user_manager.list():
            assert self.history_manager.is_accessible(published, user)

        self.log("should be able to make non-importable/inaccessible again")
        unpublished = self.history_manager.unpublish(published)
        assert unpublished == published
        assert not unpublished.published
        # note: unpublishing does not make non-importable, you must explicitly do that separately
        assert published.importable
        self.history_manager.make_non_importable(unpublished)
        assert not published.importable
        # note: slug still remains after unpublishing
        assert unpublished.slug is not None

        assert self.history_manager.is_accessible(unpublished, owner)
        assert not self.history_manager.is_accessible(unpublished, non_owner)
        assert self.history_manager.is_accessible(unpublished, self.admin_user)

    def test_sharable(self):
        owner = self.user_manager.create(**user2_data)
        self.trans.set_user(owner)
        item1 = self.history_manager.create(user=owner)

        non_owner = self.user_manager.create(**user3_data)
        # third_party = self.user_manager.create( **user4_data )

        self.log("should be unshared by default")
        assert self.history_manager.get_share_assocs(item1) == []
        assert item1.slug is None

        self.log("should be able to share with specific users")
        share_assoc = self.history_manager.share_with(item1, non_owner)
        assert isinstance(share_assoc, model.HistoryUserShareAssociation)
        assert self.history_manager.is_accessible(item1, non_owner)
        assert len(self.history_manager.get_share_assocs(item1)) == 1
        assert len(self.history_manager.get_share_assocs(item1, user=non_owner)) == 1
        assert isinstance(item1.slug, str)

        self.log("should be able to unshare with specific users")  # type: ignore[unreachable]
        share_assoc = self.history_manager.unshare_with(item1, non_owner)
        assert isinstance(share_assoc, model.HistoryUserShareAssociation)
        assert not self.history_manager.is_accessible(item1, non_owner)
        assert self.history_manager.get_share_assocs(item1) == []
        assert self.history_manager.get_share_assocs(item1, user=non_owner) == []

    # TODO: test slug formation

    def test_anon(self):
        anon_user = None
        self.trans.set_user(anon_user)

        self.log("should not allow access and owner for anon user on a history by another anon user (None)")
        anon_history1 = self.history_manager.create(user=None)
        # do not set the trans.history!
        assert not self.history_manager.is_owner(anon_history1, anon_user, current_history=self.trans.history)
        assert not self.history_manager.is_accessible(anon_history1, anon_user, current_history=self.trans.history)

        self.log("should allow access and owner for anon user on a history if it's the session's current history")
        anon_history2 = self.history_manager.create(user=anon_user)
        self.trans.set_history(anon_history2)
        assert self.history_manager.is_owner(anon_history2, anon_user, current_history=self.trans.history)
        assert self.history_manager.is_accessible(anon_history2, anon_user, current_history=self.trans.history)

        self.log("should not allow owner or access for anon user on someone elses history")
        owner = self.user_manager.create(**user2_data)
        someone_elses = self.history_manager.create(user=owner)
        assert not self.history_manager.is_owner(someone_elses, anon_user, current_history=self.trans.history)
        assert not self.history_manager.is_accessible(someone_elses, anon_user, current_history=self.trans.history)

        self.log("should allow access for anon user if the history is published or importable")
        self.history_manager.make_importable(someone_elses)
        assert self.history_manager.is_accessible(someone_elses, anon_user, current_history=self.trans.history)
        self.history_manager.publish(someone_elses)
        assert self.history_manager.is_accessible(someone_elses, anon_user, current_history=self.trans.history)

    def test_delete_and_purge(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)

        history1 = self.history_manager.create(name="history1", user=user2)
        self.trans.set_history(history1)

        self.log("should allow deletion and undeletion")
        assert not history1.deleted

        self.history_manager.delete(history1)
        assert history1.deleted

        self.history_manager.undelete(history1)
        assert not history1.deleted

        self.log("should allow purging")
        history2 = self.history_manager.create(name="history2", user=user2)
        self.history_manager.purge(history2)
        assert history2.deleted
        assert history2.purged

    def test_current(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)

        history1 = self.history_manager.create(name="history1", user=user2)
        self.trans.set_history(history1)
        history2 = self.history_manager.create(name="history2", user=user2)

        self.log("should be able to set or get the current history for a user")
        assert self.history_manager.get_current(self.trans) == history1
        assert self.history_manager.set_current(self.trans, history2) == history2
        assert self.history_manager.get_current(self.trans) == history2
        assert self.history_manager.set_current_by_id(self.trans, history1.id) == history1
        assert self.history_manager.get_current(self.trans) == history1

    def test_most_recently_used(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)

        history1 = self.history_manager.create(name="history1", user=user2)
        self.trans.set_history(history1)

        # sleep a tiny bit so update time for history2 is different from history1
        time.sleep(0.1)
        history2 = self.history_manager.create(name="history2", user=user2)

        self.log("should be able to get the most recently used (updated) history for a given user")
        assert self.history_manager.most_recent(user2) == history2
        self.history_manager.update(history1, {"name": "new name"})
        assert self.history_manager.most_recent(user2) == history1

    def test_rating(self):
        user2 = self.user_manager.create(**user2_data)
        manager = self.history_manager
        item = manager.create(name="history1", user=user2)

        self.log("should properly handle no ratings")
        assert manager.rating(item, user2) is None
        assert manager.ratings(item) == []
        assert manager.ratings_avg(item) == 0
        assert manager.ratings_count(item) == 0

        self.log("should allow rating by user")
        manager.rate(item, user2, 5)
        assert manager.rating(item, user2) == 5
        assert manager.ratings(item) == [5]
        assert manager.ratings_avg(item) == 5
        assert manager.ratings_count(item) == 1

        self.log("should allow updating")
        manager.rate(item, user2, 4)
        assert manager.rating(item, user2) == 4
        assert manager.ratings(item) == [4]
        assert manager.ratings_avg(item) == 4
        assert manager.ratings_count(item) == 1

        self.log("should reflect multiple reviews")
        user3 = self.user_manager.create(**user3_data)
        assert manager.rating(item, user3) is None
        manager.rate(item, user3, 1)
        assert manager.rating(item, user3) == 1
        assert manager.ratings(item) == [4, 1]
        assert manager.ratings_avg(item) == 2.5
        assert manager.ratings_count(item) == 2


@mock.patch("galaxy.managers.histories.HistorySerializer.url_for", mock_url_builder)
@mock.patch("galaxy.managers.hdas.HDASerializer.url_for", mock_url_builder)
class TestHistorySerializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.hda_manager = self.app[hdas.HDAManager]
        self.history_serializer = self.app[HistorySerializer]

    def test_views(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)

        self.log("should have a summary view")
        summary_view = self.history_serializer.serialize_to_view(history1, view="summary")
        self.assertKeys(summary_view, self.history_serializer.views["summary"])

        self.log("should have a detailed view")
        detailed_view = self.history_serializer.serialize_to_view(history1, view="detailed")
        self.assertKeys(detailed_view, self.history_serializer.views["detailed"])

        self.log("should have the summary view as default view")
        default_view = self.history_serializer.serialize_to_view(history1, default_view="summary")
        self.assertKeys(default_view, self.history_serializer.views["summary"])

        self.log("should have a serializer for all serializable keys")
        for key in self.history_serializer.serializable_keyset:
            instantiated_attribute = getattr(history1, key, None)
            assert key in self.history_serializer.serializers or isinstance(
                instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS
            ), f"No serializer for: {key} ({instantiated_attribute})"

    def test_views_and_keys(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)

        self.log("should be able to use keys with views")
        serialized = self.history_serializer.serialize_to_view(history1, view="summary", keys=["state_ids", "user_id"])
        self.assertKeys(serialized, self.history_serializer.views["summary"] + ["state_ids", "user_id"])

        self.log("should be able to use keys on their own")
        serialized = self.history_serializer.serialize_to_view(history1, keys=["state_ids", "user_id"])
        self.assertKeys(serialized, ["state_ids", "user_id"])

    def test_sharable(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)

        self.log("should have a serializer for all SharableModel keys")
        sharable_attrs = ["user_id", "username_and_slug", "importable", "published", "slug"]
        serialized = self.history_serializer.serialize(history1, sharable_attrs)
        self.assertKeys(serialized, sharable_attrs)

        self.log("should return user_id for user with whom it's been shared if the requester is the owner")
        non_owner = self.user_manager.create(**user3_data)
        self.history_manager.share_with(history1, non_owner)
        serialized = self.history_serializer.serialize(history1, ["users_shared_with"], user=user2)
        self.assertKeys(serialized, ["users_shared_with"])
        assert isinstance(serialized["users_shared_with"], list)
        assert serialized["users_shared_with"][0] == self.app.security.encode_id(non_owner.id)

        self.log("should not return users_shared_with if the requester is not the owner")
        serialized = self.history_serializer.serialize(history1, ["users_shared_with"], user=non_owner)
        assert not hasattr(serialized, "users_shared_with")

    def test_purgable(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)

        self.log("deleted and purged should be returned in their default states")
        keys = ["deleted", "purged"]
        serialized = self.history_serializer.serialize(history1, keys)
        assert serialized["deleted"] is False
        assert serialized["purged"] is False

        self.log("deleted and purged should return their current state")
        self.history_manager.delete(history1)
        serialized = self.history_serializer.serialize(history1, keys)
        assert serialized["deleted"] is True
        assert serialized["purged"] is False

        self.history_manager.purge(history1)
        serialized = self.history_serializer.serialize(history1, keys)
        assert serialized["deleted"] is True
        assert serialized["purged"] is True

    def test_history_serializers(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)
        all_keys = list(self.history_serializer.serializable_keyset)
        serialized = self.history_serializer.serialize(history1, all_keys, user=user2)

        self.log("everything serialized should be of the proper type")
        assert isinstance(serialized["size"], int)
        assert isinstance(serialized["nice_size"], str)

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)

    def test_history_resume(self):
        user2 = self.user_manager.create(**user2_data)
        history = self.history_manager.create(name="history", user=user2)
        # No running jobs
        history.resume_paused_jobs()
        # Mock running jobs
        with mock.patch("galaxy.model.History.paused_jobs", new_callable=mock.PropertyMock) as mock_paused_jobs:
            job = model.Job()
            job.state = model.Job.states.PAUSED
            jobs = [job]
            self.trans.sa_session.add(jobs[0])
            session = self.trans.sa_session
            with transaction(session):
                session.commit()
            assert job.state == model.Job.states.PAUSED
            mock_paused_jobs.return_value = jobs
            history.resume_paused_jobs()
            mock_paused_jobs.assert_called_once()
            assert job.state == model.Job.states.NEW, job.state  # type: ignore[comparison-overlap]  # https://github.com/python/mypy/issues/15509

    def _history_state_from_states_and_deleted(self, user, hda_state_and_deleted_tuples):
        history = self.history_manager.create(name="name", user=user)
        for state, deleted in hda_state_and_deleted_tuples:
            hda = self.hda_manager.create(history=history)
            hda = self.hda_manager.update(hda, dict(state=state, deleted=deleted))
        history_state = self.history_serializer.serialize(history, ["state"])["state"]
        return history_state

    def test_state(self):
        dataset_states = model.Dataset.states
        user2 = self.user_manager.create(**user2_data)

        ready_states = [(state, False) for state in [dataset_states.OK, dataset_states.OK]]

        self.log("a history's serialized state should be running if any of its datasets are running")
        assert "running" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.RUNNING, False)]
        )
        assert "running" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.SETTING_METADATA, False)]
        )
        assert "running" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.UPLOAD, False)]
        )

        self.log("a history's serialized state should be queued if any of its datasets are queued")
        assert "queued" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.QUEUED, False)]
        )

        self.log("a history's serialized state should be error if any of its datasets are errored")
        assert "error" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.ERROR, False)]
        )
        assert "error" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.FAILED_METADATA, False)]
        )

        self.log("a history's serialized state should be ok if *all* of its datasets are ok")
        assert "ok" == self._history_state_from_states_and_deleted(user2, ready_states)

        self.log("a history's serialized state should be not be affected by deleted datasets")
        assert "ok" == self._history_state_from_states_and_deleted(
            user2, ready_states + [(dataset_states.RUNNING, True)]
        )

    def test_contents(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)

        self.log("a history with no contents should be properly reflected in empty, etc.")
        keys = ["empty", "count", "state_ids", "state_details", "state", "hdas"]
        serialized = self.history_serializer.serialize(history1, keys)
        assert serialized["state"] == "new"
        assert serialized["empty"] is True
        assert serialized["count"] == 0
        assert sum(serialized["state_details"].values()) == 0
        assert serialized["state_ids"]["ok"] == []
        assert isinstance(serialized["hdas"], list)

        self.log("a history with contents should be properly reflected in empty, etc.")
        hda1 = self.hda_manager.create(history=history1)
        self.hda_manager.update(hda1, dict(state="ok"))

        serialized = self.history_serializer.serialize(history1, keys)
        assert serialized["state"] == "ok"
        assert serialized["empty"] is False
        assert serialized["count"] == 1
        assert serialized["state_details"]["ok"] == 1
        assert isinstance(serialized["state_ids"]["ok"], list)
        assert isinstance(serialized["hdas"], list)
        assert isinstance(serialized["hdas"][0], str)

        serialized = self.history_serializer.serialize(history1, ["contents"])
        self.assertHasKeys(serialized["contents"][0], ["id", "name", "state", "create_time"])

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)

    def test_ratings(self):
        user2 = self.user_manager.create(**user2_data)
        user3 = self.user_manager.create(**user3_data)
        manager = self.history_manager
        serializer = self.history_serializer
        item = manager.create(name="history1", user=user2)

        self.log("serialization should reflect no ratings")
        serialized = serializer.serialize(item, ["user_rating", "community_rating"], user=user2)
        assert serialized["user_rating"] is None
        assert serialized["community_rating"]["count"] == 0
        assert serialized["community_rating"]["average"] == 0.0

        self.log("serialization should reflect ratings")
        manager.rate(item, user2, 1)
        manager.rate(item, user3, 4)
        serialized = serializer.serialize(item, ["user_rating", "community_rating"], user=user2)
        assert serialized["user_rating"] == 1
        assert serialized["community_rating"]["count"] == 2
        assert serialized["community_rating"]["average"] == 2.5
        self.assertIsJsonifyable(serialized)

        self.log("serialization of user_rating without user should error")
        with self.assertRaises(base.ModelSerializingError):
            serializer.serialize(item, ["user_rating"])


# =============================================================================
class TestHistoryDeserializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.history_deserializer = self.app[HistoryDeserializer]

    def test_ratings(self):
        user2 = self.user_manager.create(**user2_data)
        manager = self.history_manager
        deserializer = self.history_deserializer
        item = manager.create(name="history1", user=user2)

        self.log("deserialization should allow ratings change")
        deserializer.deserialize(item, {"user_rating": 4}, user=user2)
        assert manager.rating(item, user2) == 4
        assert manager.ratings(item) == [4]
        assert manager.ratings_avg(item) == 4
        assert manager.ratings_count(item) == 1

        self.log("deserialization should fail silently on community_rating")
        deserializer.deserialize(item, {"community_rating": 4}, user=user2)
        assert manager.ratings_count(item) == 1

    def test_sharable(self):
        manager = self.history_manager
        deserializer = self.history_deserializer

        user2 = self.user_manager.create(**user2_data)
        item = manager.create(name="history1", user=user2)
        non_owner = self.user_manager.create(**user3_data)

        self.log("should allow adding a share by adding a user id to users_shared_with")
        non_owner_id = self.app.security.encode_id(non_owner.id)
        deserializer.deserialize(item, {"users_shared_with": [non_owner_id]}, user=user2)
        user_shares = manager.get_share_assocs(item)
        assert len(user_shares) == 1
        assert user_shares[0].user_id == non_owner.id

        self.log("re-adding an existing user id should do nothing")
        deserializer.deserialize(item, {"users_shared_with": [non_owner_id, non_owner_id]}, user=user2)
        user_shares = manager.get_share_assocs(item)
        assert len(user_shares) == 1
        assert user_shares[0].user_id == non_owner.id

        self.log("should allow removing a share by not having it in users_shared_with")
        deserializer.deserialize(item, {"users_shared_with": []}, user=user2)
        user_shares = manager.get_share_assocs(item)
        assert len(user_shares) == 0

        self.log("adding a bad user id should error")
        with self.assertRaises(exceptions.MalformedId):
            deserializer.deserialize(item, {"users_shared_with": [None]}, user=user2)

        self.log("adding a non-existing user id should do nothing")
        non_user_id = self.app.security.encode_id(99)
        deserializer.deserialize(item, {"users_shared_with": [non_user_id]}, user=user2)
        user_shares = manager.get_share_assocs(item)
        assert len(user_shares) == 0


# =============================================================================
class TestHistoryFilters(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.filter_parser = self.app[HistoryFilters]

    # ---- functional and orm filter splitting and resolution
    def test_parse_filters(self):
        filters = self.filter_parser.parse_filters(
            [("name", "eq", "wot"), ("deleted", "eq", "True"), ("annotation", "has", "hrrmm")]
        )
        self.log("both orm and fn filters should be parsed and returned")
        assert len(filters) == 3

        self.log("values should be parsed")
        assert isinstance(filters[1].filter.right, sqlalchemy.sql.elements.True_)

    def test_parse_filters_invalid_filters(self):
        self.log("should error on non-column attr")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.filter_parser.parse_filters(
                [
                    ("merp", "eq", "wot"),
                ],
            )
        self.log("should error on non-allowlisted attr")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.filter_parser.parse_filters(
                [
                    ("user_id", "eq", "wot"),
                ],
            )
        self.log("should error on non-allowlisted op")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.filter_parser.parse_filters(
                [
                    ("name", "lt", "wot"),
                ],
            )
        self.log("should error on non-listed fn op")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.filter_parser.parse_filters(
                [
                    ("annotation", "like", "wot"),
                ],
            )
        self.log("should error on val parsing error")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.filter_parser.parse_filters(
                [
                    ("deleted", "eq", "wot"),
                ],
            )

    def test_orm_filter_parsing(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)
        history2 = self.history_manager.create(name="history2", user=user2)
        history3 = self.history_manager.create(name="history3", user=user2)

        filters = self.filter_parser.parse_filters(
            [
                ("name", "like", "history%"),
            ]
        )
        histories = self.history_manager.list(filters=filters)
        assert histories == [history1, history2, history3]

        filters = self.filter_parser.parse_filters(
            [
                ("name", "like", "%2"),
            ]
        )
        assert self.history_manager.list(filters=filters) == [history2]

        filters = self.filter_parser.parse_filters(
            [
                ("name", "eq", "history2"),
            ]
        )
        assert self.history_manager.list(filters=filters) == [history2]

        self.history_manager.update(history1, dict(deleted=True))
        filters = self.filter_parser.parse_filters(
            [
                ("deleted", "eq", "True"),
            ]
        )
        assert self.history_manager.list(filters=filters) == [history1]
        filters = self.filter_parser.parse_filters(
            [
                ("deleted", "eq", "False"),
            ]
        )
        assert self.history_manager.list(filters=filters) == [history2, history3]
        assert self.history_manager.list() == [history1, history2, history3]

        self.history_manager.update(history3, dict(deleted=True))
        self.history_manager.update(history1, dict(importable=True))
        self.history_manager.update(history2, dict(importable=True))
        filters = self.filter_parser.parse_filters(
            [
                ("deleted", "eq", "True"),
                ("importable", "eq", "True"),
            ]
        )
        assert self.history_manager.list(filters=filters) == [history1]
        assert self.history_manager.list() == [history1, history2, history3]

    def test_fn_filter_parsing(self):
        user2 = self.user_manager.create(**user2_data)
        user3 = self.user_manager.create(**user3_data)
        history1 = self.history_manager.create(name="history1", user=user2)
        history2 = self.history_manager.create(name="history2", user=user2)
        history3 = self.history_manager.create(name="history3", user=user2)
        history4 = self.history_manager.create(name="history4", user=user3)

        # test username eq filter
        filters_2 = self.filter_parser.parse_filters(
            [
                ("username", "eq", "user2"),
            ]
        )
        filters_3 = self.filter_parser.parse_filters(
            [
                ("username", "eq", "user3"),
            ]
        )
        username_filter_2 = filters_2[0].filter
        username_filter_3 = filters_3[0].filter

        assert username_filter_2(history1)
        assert username_filter_2(history2)
        assert username_filter_2(history3)
        assert not username_filter_2(history4)
        assert not username_filter_3(history1)
        assert not username_filter_3(history2)
        assert not username_filter_3(history3)
        assert username_filter_3(history4)

        assert self.history_manager.list(filters=filters_2) == [history1, history2, history3]
        assert self.history_manager.list(filters=filters_3) == [history4]

        # test username contains filter
        filters = self.filter_parser.parse_filters(
            [
                ("username", "contains", "user"),
            ]
        )

        assert self.history_manager.list(filters=filters) == [history1, history2, history3, history4]

        # test username eq filter (inequality)
        filters = self.filter_parser.parse_filters(
            [
                ("username", "eq", "user"),
            ]
        )

        assert self.history_manager.list(filters=filters) == []

        # test annotation filter
        filters = self.filter_parser.parse_filters(
            [
                ("annotation", "has", "no play"),
            ]
        )
        anno_filter = filters[0].filter

        history3.add_item_annotation(self.trans.sa_session, user2, history3, "All work and no play")
        session = self.trans.sa_session
        with transaction(session):
            session.commit()

        assert anno_filter(history3)
        assert not anno_filter(history2)

        assert self.history_manager.list(filters=filters) == [history3]

        self.log("should allow combinations of orm and fn filters")
        self.history_manager.update(history3, dict(importable=True))
        self.history_manager.update(history2, dict(importable=True))
        history1.add_item_annotation(self.trans.sa_session, user2, history1, "All work and no play")
        session = self.trans.sa_session
        with transaction(session):
            session.commit()

        shining_examples = self.history_manager.list(
            filters=self.filter_parser.parse_filters(
                [
                    ("importable", "eq", "True"),
                    ("annotation", "has", "no play"),
                ]
            )
        )
        assert shining_examples == [history3]

        case_insensitive_examples = self.history_manager.list(
            filters=self.filter_parser.parse_filters(
                [
                    ("annotation", "contains", "all"),
                ]
            )
        )
        assert case_insensitive_examples == [history1, history3]

    def test_fn_filter_currying(self):
        self.filter_parser.fn_filter_parsers = {"name_len": {"op": {"lt": lambda i, v: len(i.name) < v}, "val": int}}
        self.log("should be 2 filters now")
        assert len(self.filter_parser.fn_filter_parsers) == 1
        filters = self.filter_parser.parse_filters([("name_len", "lt", "4")])
        self.log("should have parsed out a single filter")
        assert len(filters) == 1

        filter_ = filters[0].filter
        fake = mock.Mock()
        fake.name = "123"
        self.log("123 should return true through the filter")
        assert filter_(fake)
        fake.name = "1234"
        self.log("1234 should return false through the filter")
        assert not filter_(fake)

    def test_list(self):
        """
        Test limit and offset in conjunction with both orm and fn filtering.
        """
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)
        history2 = self.history_manager.create(name="history2", user=user2)
        history3 = self.history_manager.create(name="history3", user=user2)
        history4 = self.history_manager.create(name="history4", user=user2)

        self.history_manager.delete(history1)
        self.history_manager.delete(history2)
        self.history_manager.delete(history3)

        test_annotation = "testing"
        history2.add_item_annotation(self.trans.sa_session, user2, history2, test_annotation)
        session = self.trans.sa_session
        with transaction(session):
            session.commit()
        history3.add_item_annotation(self.trans.sa_session, user2, history3, test_annotation)
        session = self.trans.sa_session
        with transaction(session):
            session.commit()
        history3.add_item_annotation(self.trans.sa_session, user2, history4, test_annotation)
        session = self.trans.sa_session
        with transaction(session):
            session.commit()

        all_histories = [history1, history2, history3, history4]
        deleted_and_annotated = [history2, history3]

        self.log("no offset, no limit should work")
        assert self.history_manager.list(offset=None, limit=None) == all_histories
        assert self.history_manager.list() == all_histories
        self.log("no offset, limit should work")
        assert self.history_manager.list(limit=2) == [history1, history2]
        self.log("offset, no limit should work")
        assert self.history_manager.list(offset=1) == [history2, history3, history4]
        self.log("offset, limit should work")
        assert self.history_manager.list(offset=1, limit=1) == [history2]

        self.log("zero limit should return empty list")
        assert self.history_manager.list(limit=0) == []
        self.log("past len offset should return empty list")
        assert self.history_manager.list(offset=len(all_histories)) == []
        self.log("negative limit should return full list")
        assert self.history_manager.list(limit=-1) == all_histories
        self.log("negative offset should return full list")
        assert self.history_manager.list(offset=-1) == all_histories

        filters = [model.History.deleted == true()]
        self.log("orm filtered, no offset, no limit should work")
        found = self.history_manager.list(filters=filters)
        assert found == [history1, history2, history3]
        self.log("orm filtered, no offset, limit should work")
        found = self.history_manager.list(filters=filters, limit=2)
        assert found == [history1, history2]
        self.log("orm filtered, offset, no limit should work")
        found = self.history_manager.list(filters=filters, offset=1)
        assert found == [history2, history3]
        self.log("orm filtered, offset, limit should work")
        found = self.history_manager.list(filters=filters, offset=1, limit=1)
        assert found == [history2]

        filters = self.filter_parser.parse_filters([("annotation", "has", test_annotation)])
        self.log("fn filtered, no offset, no limit should work")
        found = self.history_manager.list(filters=filters)
        assert found == [history2, history3, history4]
        self.log("fn filtered, no offset, limit should work")
        found = self.history_manager.list(filters=filters, limit=2)
        assert found == [history2, history3]
        self.log("fn filtered, offset, no limit should work")
        found = self.history_manager.list(filters=filters, offset=1)
        assert found == [history3, history4]
        self.log("fn filtered, offset, limit should work")
        found = self.history_manager.list(filters=filters, offset=1, limit=1)
        assert found == [history3]

        filters = self.filter_parser.parse_filters([("deleted", "eq", "True"), ("annotation", "has", test_annotation)])
        self.log("orm and fn filtered, no offset, no limit should work")
        found = self.history_manager.list(filters=filters)
        assert found == [history2, history3]
        self.log("orm and fn filtered, no offset, limit should work")
        found = self.history_manager.list(filters=filters, limit=1)
        assert found == [history2]
        self.log("orm and fn filtered, offset, no limit should work")
        found = self.history_manager.list(filters=filters, offset=1)
        assert found == [history3]
        self.log("orm and fn filtered, offset, limit should work")
        found = self.history_manager.list(filters=filters, offset=1, limit=1)
        assert found == [history3]

        self.log("orm and fn filtered, zero limit should return empty list")
        found = self.history_manager.list(filters=filters, limit=0)
        assert found == []
        self.log("orm and fn filtered, past len offset should return empty list")
        found = self.history_manager.list(filters=filters, offset=len(deleted_and_annotated))
        assert found == []
        self.log("orm and fn filtered, negative limit should return full list")
        found = self.history_manager.list(filters=filters, limit=-1)
        assert found == deleted_and_annotated
        self.log("orm and fn filtered, negative offset should return full list")
        found = self.history_manager.list(filters=filters, offset=-1)
        assert found == deleted_and_annotated

    def test_count(self):
        user2 = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=user2)
        history2 = self.history_manager.create(name="history2", user=user2)
        history3 = self.history_manager.create(name="history3", user=user2)
        history4 = self.history_manager.create(name="history4", user=user2)
        history5 = self.history_manager.create(name="history5", user=user2)

        self.history_manager.delete(history1)
        self.history_manager.delete(history2)
        self.history_manager.archive_history(history3, None)
        self.history_manager.archive_history(history4, None)

        test_annotation = "testing"
        history2.add_item_annotation(self.trans.sa_session, user2, history2, test_annotation)
        self.trans.sa_session.flush()
        history3.add_item_annotation(self.trans.sa_session, user2, history3, test_annotation)
        self.trans.sa_session.flush()
        history3.add_item_annotation(self.trans.sa_session, user2, history4, test_annotation)
        self.trans.sa_session.flush()

        all_histories = [history1, history2, history3, history4, history5]
        deleted = [history1, history2]
        archived = [history3, history4]

        assert self.history_manager.count() == len(all_histories), "having no filters should count all histories"
        filters = [model.History.deleted == true()]
        assert self.history_manager.count(filters=filters) == len(deleted)
        filters = [model.History.archived == true()]
        assert self.history_manager.count(filters=filters) == len(archived)
        filters = [model.History.deleted == false(), model.History.archived == false()]
        assert self.history_manager.count(filters=filters) == len(all_histories) - len(deleted) - len(archived)

        raw_annotation_fn_filter = ("annotation", "has", test_annotation)
        # functional filtering is not supported
        with pytest.raises(exceptions.RequestParameterInvalidException) as exc_info:
            filters = self.filter_parser.parse_filters([raw_annotation_fn_filter])
            self.history_manager.count(filters=filters)
            assert "not supported" in str(exc_info)

        raw_deleted_orm_filter = ("deleted", "eq", "True")
        with pytest.raises(exceptions.RequestParameterInvalidException) as exc_info:
            filters = self.filter_parser.parse_filters([raw_deleted_orm_filter, raw_annotation_fn_filter])
            self.history_manager.count(filters=filters)
            assert "not supported" in str(exc_info)
