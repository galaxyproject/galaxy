import collections
import os
import random
import unittest
import uuid
from tempfile import NamedTemporaryFile
from typing import List

import pytest
from sqlalchemy import (
    inspect,
    select,
)

import galaxy.datatypes.registry
import galaxy.model
import galaxy.model.mapping as mapping
from galaxy import model
from galaxy.model.database_utils import create_database
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.orm.util import (
    add_object_to_object_session,
    get_object_session,
)
from galaxy.model.security import GalaxyRBACAgent

datatypes_registry = galaxy.datatypes.registry.Registry()
datatypes_registry.load_datatypes()
galaxy.model.set_datatypes_registry(datatypes_registry)

DB_URI = "sqlite:///:memory:"
# docker run -e POSTGRES_USER=galaxy -p 5432:5432 -d postgres
# GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE='postgresql://galaxy@localhost:5432/' pytest test/unit/data/test_galaxy_mapping.py
skip_if_not_postgres_base = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE"),
    reason="GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE not set",
)


class BaseModelTestCase(unittest.TestCase):
    model: mapping.GalaxyModelMapping

    @classmethod
    def _db_uri(cls):
        return DB_URI

    @classmethod
    def setUpClass(cls):
        # Start the database and connect the mapping
        cls.model = mapping.init("/tmp", cls._db_uri(), create_tables=True, object_store=MockObjectStore())
        assert cls.model.engine is not None

    @classmethod
    def query(cls, type):
        return cls.model.session.query(type)

    @classmethod
    def persist(cls, *args, **kwargs):
        session = cls.session()
        flush = kwargs.get("flush", True)
        for arg in args:
            session.add(arg)
            if flush:
                session.flush()
        if kwargs.get("expunge", not flush):
            cls.expunge()
        return arg  # Return last or only arg.

    @classmethod
    def session(cls):
        return cls.model.session

    @classmethod
    def expunge(cls):
        cls.model.session.flush()
        cls.model.session.expunge_all()


class MappingTests(BaseModelTestCase):
    def test_ratings(self):
        user_email = "rater@example.com"
        u = model.User(email=user_email, password="password")
        self.persist(u)

        def persist_and_check_rating(rating_class, item):
            rating = 5
            rating_association = rating_class(u, item, rating)
            self.persist(rating_association)
            self.expunge()
            stored_rating = self.query(rating_class).all()[0]
            assert stored_rating.rating == rating
            assert stored_rating.user.email == user_email

        sw = model.StoredWorkflow()
        add_object_to_object_session(sw, u)
        sw.user = u
        self.persist(sw)
        persist_and_check_rating(model.StoredWorkflowRatingAssociation, sw)

        h = model.History(name="History for Rating", user=u)
        self.persist(h)
        persist_and_check_rating(model.HistoryRatingAssociation, h)

        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(d1)
        persist_and_check_rating(model.HistoryDatasetAssociationRatingAssociation, d1)

        page = model.Page()
        page.user = u
        self.persist(page)
        persist_and_check_rating(model.PageRatingAssociation, page)

        visualization = model.Visualization()
        visualization.user = u
        self.persist(visualization)
        persist_and_check_rating(model.VisualizationRatingAssociation, visualization)

        dataset_collection = model.DatasetCollection(collection_type="paired")
        history_dataset_collection = model.HistoryDatasetCollectionAssociation(collection=dataset_collection)
        self.persist(history_dataset_collection)
        persist_and_check_rating(model.HistoryDatasetCollectionRatingAssociation, history_dataset_collection)

        library_dataset_collection = model.LibraryDatasetCollectionAssociation(collection=dataset_collection)
        self.persist(library_dataset_collection)
        persist_and_check_rating(model.LibraryDatasetCollectionRatingAssociation, library_dataset_collection)

    def test_display_name(self):
        def assert_display_name_converts_to_unicode(item, name):
            assert isinstance(item.get_display_name(), str)
            assert item.get_display_name() == name

        ldda = model.LibraryDatasetDatasetAssociation(name="ldda_name")
        assert_display_name_converts_to_unicode(ldda, "ldda_name")

        hda = model.HistoryDatasetAssociation(name="hda_name")
        assert_display_name_converts_to_unicode(hda, "hda_name")

        history = model.History(name="history_name")
        assert_display_name_converts_to_unicode(history, "history_name")

        library = model.Library(name="library_name")
        assert_display_name_converts_to_unicode(library, "library_name")

        library_folder = model.LibraryFolder(name="library_folder")
        assert_display_name_converts_to_unicode(library_folder, "library_folder")

        history = model.History(name="Hello₩◎ґʟⅾ")

        assert isinstance(history.name, str)
        assert isinstance(history.get_display_name(), str)
        assert history.get_display_name() == "Hello₩◎ґʟⅾ"

    def test_hda_to_library_dataset_dataset_association(self):
        u = model.User(email="mary@example.com", password="password")
        hda = model.HistoryDatasetAssociation(name="hda_name")
        self.persist(hda)
        trans = collections.namedtuple("trans", "user")
        target_folder = model.LibraryFolder(name="library_folder")
        ldda = hda.to_library_dataset_dataset_association(
            trans=trans(user=u),
            target_folder=target_folder,
        )
        assert target_folder.item_count == 1
        assert ldda.id
        assert ldda.library_dataset.id
        assert ldda.library_dataset_id
        assert ldda.library_dataset.library_dataset_dataset_association
        assert ldda.library_dataset.library_dataset_dataset_association_id
        library_dataset_id = ldda.library_dataset_id
        replace_dataset = ldda.library_dataset
        new_ldda = hda.to_library_dataset_dataset_association(
            trans=trans(user=u), target_folder=target_folder, replace_dataset=replace_dataset
        )
        assert new_ldda.id != ldda.id
        assert new_ldda.library_dataset_id == library_dataset_id
        assert new_ldda.library_dataset.library_dataset_dataset_association_id == new_ldda.id
        assert len(new_ldda.library_dataset.expired_datasets) == 1
        assert new_ldda.library_dataset.expired_datasets[0] == ldda
        assert target_folder.item_count == 1

    def test_tags(self):
        TAG_NAME = "Test Tag"
        my_tag = model.Tag(name=TAG_NAME)
        u = model.User(email="tagger@example.com", password="password")
        self.persist(my_tag, u)

        def tag_and_test(taggable_object, tag_association_class):
            q = select(tag_association_class).join(model.Tag).where(model.Tag.name == TAG_NAME)

            assert len(self.model.session.execute(q).all()) == 0

            tag_association = tag_association_class()
            tag_association.tag = my_tag
            taggable_object.tags = [tag_association]
            self.persist(tag_association, taggable_object)

            assert len(self.model.session.execute(q).all()) == 1

        sw = model.StoredWorkflow(user=u)
        tag_and_test(sw, model.StoredWorkflowTagAssociation)

        h = model.History(name="History for Tagging", user=u)
        tag_and_test(h, model.HistoryTagAssociation)

        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        tag_and_test(d1, model.HistoryDatasetAssociationTagAssociation)

        page = model.Page(user=u)
        tag_and_test(page, model.PageTagAssociation)

        visualization = model.Visualization(user=u)
        tag_and_test(visualization, model.VisualizationTagAssociation)

        dataset_collection = model.DatasetCollection(collection_type="paired")
        history_dataset_collection = model.HistoryDatasetCollectionAssociation(collection=dataset_collection)
        tag_and_test(history_dataset_collection, model.HistoryDatasetCollectionTagAssociation)

        library_dataset_collection = model.LibraryDatasetCollectionAssociation(collection=dataset_collection)
        tag_and_test(library_dataset_collection, model.LibraryDatasetCollectionTagAssociation)

    def test_collection_get_interface(self):
        u = model.User(email="mary@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        c1 = model.DatasetCollection(collection_type="list")
        elements = 100
        dces = [
            model.DatasetCollectionElement(collection=c1, element=d1, element_identifier=f"{i}", element_index=i)
            for i in range(elements)
        ]
        self.persist(u, h1, d1, c1, *dces, flush=False, expunge=False)
        self.model.session.flush()
        for i in range(elements):
            assert c1[i] == dces[i]

    def test_dataset_instance_order(self):
        u = model.User(email="mary@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        elements = []
        list_pair = model.DatasetCollection(collection_type="list:paired")
        for i in range(20):
            pair = model.DatasetCollection(collection_type="pair")
            forward = model.HistoryDatasetAssociation(
                extension="txt", history=h1, name=f"forward_{i}", create_dataset=True, sa_session=self.model.session
            )
            reverse = model.HistoryDatasetAssociation(
                extension="bam", history=h1, name=f"reverse_{i}", create_dataset=True, sa_session=self.model.session
            )
            dce1 = model.DatasetCollectionElement(
                collection=pair, element=forward, element_identifier=f"forward_{i}", element_index=1
            )
            dce2 = model.DatasetCollectionElement(
                collection=pair, element=reverse, element_identifier=f"reverse_{i}", element_index=2
            )
            to_persist = [(forward, reverse), (dce1, dce2)]
            self.persist(pair)
            for pair_item in to_persist:
                if i % 2:
                    self.persist(pair_item[0])
                    self.persist(pair_item[1])
                else:
                    self.persist(pair_item[1])
                    self.persist(pair_item[0])
            elements.append(
                model.DatasetCollectionElement(
                    collection=list_pair, element=pair, element_index=i, element_identifier=str(i)
                )
            )
        self.persist(list_pair)
        random.shuffle(elements)
        for item in elements:
            self.persist(item)
        forward_hdas: List[model.HistoryDatasetAssociation] = []
        reverse_hdas: List[model.HistoryDatasetAssociation] = []
        for i, dataset_instance in enumerate(list_pair.dataset_instances):
            if i % 2:
                reverse_hdas.append(dataset_instance)
            else:
                forward_hdas.append(dataset_instance)
        assert all(d.name == f"forward_{i}" for i, d in enumerate(forward_hdas))
        assert all(d.name == f"reverse_{i}" for i, d in enumerate(reverse_hdas))

    def test_collections_in_histories(self):
        u = model.User(email="mary@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        d2 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )

        c1 = model.DatasetCollection(collection_type="pair")
        hc1 = model.HistoryDatasetCollectionAssociation(history=h1, collection=c1, name="HistoryCollectionTest1")

        dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="left")
        dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="right")

        self.persist(u, h1, d1, d2, c1, hc1, dce1, dce2)

        loaded_dataset_collection = (
            self.query(model.HistoryDatasetCollectionAssociation)
            .filter(model.HistoryDatasetCollectionAssociation.name == "HistoryCollectionTest1")
            .first()
            .collection
        )
        self.assertEqual(len(loaded_dataset_collection.elements), 2)
        assert loaded_dataset_collection.collection_type == "pair"
        assert loaded_dataset_collection["left"] == dce1
        assert loaded_dataset_collection["right"] == dce2

    def test_collections_in_library_folders(self):
        u = model.User(email="mary2@example.com", password="password")
        lf = model.LibraryFolder(name="RootFolder")
        library = model.Library(name="Library1", root_folder=lf)
        ld1 = model.LibraryDataset()
        ld2 = model.LibraryDataset()

        ldda1 = model.LibraryDatasetDatasetAssociation(extension="txt", library_dataset=ld1)
        ldda2 = model.LibraryDatasetDatasetAssociation(extension="txt", library_dataset=ld1)

        c1 = model.DatasetCollection(collection_type="pair")
        dce1 = model.DatasetCollectionElement(collection=c1, element=ldda1)
        dce2 = model.DatasetCollectionElement(collection=c1, element=ldda2)
        self.persist(u, library, lf, ld1, ld2, c1, ldda1, ldda2, dce1, dce2)

        # TODO:
        # loaded_dataset_collection = self.query( model.DatasetCollection ).filter( model.DatasetCollection.name == "LibraryCollectionTest1" ).first()
        # self.assertEqual(len(loaded_dataset_collection.datasets), 2)
        # assert loaded_dataset_collection.collection_type == "pair"

    def test_nested_collection_attributes(self):
        u = model.User(email="mary2@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="bam", history=h1, create_dataset=True, sa_session=self.model.session
        )
        index = NamedTemporaryFile("w")
        index.write("cool bam index")
        index2 = NamedTemporaryFile("w")
        index2.write("cool bam index 2")
        metadata_dict = {
            "bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index.name}),
            "bam_csi_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index2.name}),
        }
        d1.metadata.from_JSON_dict(json_dict=metadata_dict)
        assert d1.metadata.bam_index
        assert d1.metadata.bam_csi_index
        assert isinstance(d1.metadata.bam_index, model.MetadataFile)
        assert isinstance(d1.metadata.bam_csi_index, model.MetadataFile)
        d2 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        c1 = model.DatasetCollection(collection_type="paired")
        dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
        dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)
        c2 = model.DatasetCollection(collection_type="list:paired")
        dce3 = model.DatasetCollectionElement(
            collection=c2, element=c1, element_identifier="inner_list", element_index=0
        )
        c3 = model.DatasetCollection(collection_type="list:list")
        c4 = model.DatasetCollection(collection_type="list:list:paired")
        dce4 = model.DatasetCollectionElement(
            collection=c4, element=c2, element_identifier="outer_list", element_index=0
        )
        self.model.session.add_all([d1, d2, c1, dce1, dce2, c2, dce3, c3, c4, dce4])
        self.model.session.flush()
        q = c2._get_nested_collection_attributes(
            element_attributes=("element_identifier",), hda_attributes=("extension",), dataset_attributes=("state",)
        )
        assert [(r._fields) for r in q] == [
            ("element_identifier_0", "element_identifier_1", "extension", "state"),
            ("element_identifier_0", "element_identifier_1", "extension", "state"),
        ]
        assert q.all() == [("inner_list", "forward", "bam", "new"), ("inner_list", "reverse", "txt", "new")]
        q = c2._get_nested_collection_attributes(return_entities=(model.HistoryDatasetAssociation,))
        assert q.all() == [d1, d2]
        q = c2._get_nested_collection_attributes(return_entities=(model.HistoryDatasetAssociation, model.Dataset))
        assert q.all() == [(d1, d1.dataset), (d2, d2.dataset)]
        # Assert properties that use _get_nested_collection_attributes return correct content
        assert c2.dataset_instances == [d1, d2]
        assert c2.dataset_elements == [dce1, dce2]
        assert c2.dataset_action_tuples == []
        assert c2.populated_optimized
        assert c2.dataset_states_and_extensions_summary == ({"new"}, {"txt", "bam"})
        assert c2.element_identifiers_extensions_paths_and_metadata_files == [
            [
                ("inner_list", "forward"),
                "bam",
                "mock_dataset_14.dat",
                [("bai", "mock_dataset_14.dat"), ("bam.csi", "mock_dataset_14.dat")],
            ],
            [("inner_list", "reverse"), "txt", "mock_dataset_14.dat", []],
        ]
        assert c3.dataset_instances == []
        assert c3.dataset_elements == []
        assert c3.dataset_states_and_extensions_summary == (set(), set())
        q = c4._get_nested_collection_attributes(element_attributes=("element_identifier",))
        assert q.all() == [("outer_list", "inner_list", "forward"), ("outer_list", "inner_list", "reverse")]
        assert c4.dataset_elements == [dce1, dce2]
        assert c4.element_identifiers_extensions_and_paths == [
            (("outer_list", "inner_list", "forward"), "bam", "mock_dataset_14.dat"),
            (("outer_list", "inner_list", "reverse"), "txt", "mock_dataset_14.dat"),
        ]

    def test_dataset_dbkeys_and_extensions_summary(self):
        u = model.User(email="mary2@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="bam", dbkey="hg19", history=h1, create_dataset=True, sa_session=self.model.session
        )
        d2 = model.HistoryDatasetAssociation(
            extension="txt", dbkey="hg19", history=h1, create_dataset=True, sa_session=self.model.session
        )
        c1 = model.DatasetCollection(collection_type="paired")
        dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
        dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)
        hdca = model.HistoryDatasetCollectionAssociation(collection=c1, history=h1)
        self.model.session.add_all([d1, d2, c1, dce1, dce2, hdca])
        self.model.session.flush()
        assert hdca.dataset_dbkeys_and_extensions_summary[0] == {"hg19"}
        assert hdca.dataset_dbkeys_and_extensions_summary[1] == {"bam", "txt"}

    def test_populated_optimized_ok(self):
        u = model.User(email="mary2@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        d2 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        c1 = model.DatasetCollection(collection_type="paired")
        dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
        dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)
        self.model.session.add_all([d1, d2, c1, dce1, dce2])
        self.model.session.flush()
        assert c1.populated
        assert c1.populated_optimized

    def test_populated_optimized_empty_list_list_ok(self):
        c1 = model.DatasetCollection(collection_type="list")
        c2 = model.DatasetCollection(collection_type="list:list")
        dce1 = model.DatasetCollectionElement(
            collection=c2, element=c1, element_identifier="empty_list", element_index=0
        )
        self.model.session.add_all([c1, c2, dce1])
        self.model.session.flush()
        assert c1.populated
        assert c1.populated_optimized
        assert c2.populated
        assert c2.populated_optimized

    def test_populated_optimized_list_list_not_populated(self):
        c1 = model.DatasetCollection(collection_type="list")
        c1.populated_state = False
        c2 = model.DatasetCollection(collection_type="list:list")
        dce1 = model.DatasetCollectionElement(
            collection=c2, element=c1, element_identifier="empty_list", element_index=0
        )
        self.model.session.add_all([c1, c2, dce1])
        self.model.session.flush()
        assert not c1.populated
        assert not c1.populated_optimized
        assert not c2.populated
        assert not c2.populated_optimized

    def test_default_disk_usage(self):
        u = model.User(email="disk_default@test.com", password="password")
        self.persist(u)
        u.adjust_total_disk_usage(1)
        u_id = u.id
        self.expunge()
        user_reload = self.model.session.query(model.User).get(u_id)
        assert user_reload.disk_usage == 1

    def test_basic(self):
        original_user_count = len(self.model.session.query(model.User).all())

        # Make some changes and commit them
        u = model.User(email="james@foo.bar.baz", password="password")
        # gs = model.GalaxySession()
        h1 = model.History(name="History 1", user=u)
        # h1.queries.append( model.Query( "h1->q1" ) )
        # h1.queries.append( model.Query( "h1->q2" ) )
        h2 = model.History(name=("H" * 1024))
        self.persist(u, h1, h2)
        # q1 = model.Query( "h2->q1" )
        metadata = dict(chromCol=1, startCol=2, endCol=3)
        d1 = model.HistoryDatasetAssociation(
            extension="interval", metadata=metadata, history=h2, create_dataset=True, sa_session=self.model.session
        )
        # h2.queries.append( q1 )
        # h2.queries.append( model.Query( "h2->q2" ) )
        self.persist(d1)

        # Check
        users = self.model.session.query(model.User).all()
        assert len(users) == original_user_count + 1
        user = [user for user in users if user.email == "james@foo.bar.baz"][0]
        assert user.email == "james@foo.bar.baz"
        assert user.password == "password"
        assert len(user.histories) == 1
        assert user.histories[0].name == "History 1"
        hists = self.model.session.query(model.History).all()
        hist0 = [history for history in hists if history.name == "History 1"][0]
        hist1 = [history for history in hists if history.name == "H" * 255][0]
        assert hist0.name == "History 1"
        assert hist1.name == ("H" * 255)
        assert hist0.user == user
        assert hist1.user is None
        assert hist1.datasets[0].metadata.chromCol == 1
        # The filename test has moved to objectstore
        # id = hist1.datasets[0].id
        # assert hist1.datasets[0].file_name == os.path.join( "/tmp", *directory_hash_id( id ) ) + ( "/dataset_%d.dat" % id )
        # Do an update and check
        hist1.name = "History 2b"
        self.expunge()
        hists = self.model.session.query(model.History).all()
        hist0 = [history for history in hists if history.name == "History 1"][0]
        hist1 = [history for history in hists if history.name == "History 2b"][0]
        assert hist0.name == "History 1"
        assert hist1.name == "History 2b"
        # gvk TODO need to ad test for GalaxySessions, but not yet sure what they should look like.

    def test_metadata_spec(self):
        metadata = dict(chromCol=1, startCol=2, endCol=3)
        d = model.HistoryDatasetAssociation(extension="interval", metadata=metadata, sa_session=self.model.session)
        assert d.metadata.chromCol == 1
        assert d.metadata.anyAttribute is None
        assert "items" not in d.metadata

    def test_dataset_job_relationship(self):
        dataset = model.Dataset()
        job = model.Job()
        dataset.job = job
        self.persist(job, dataset)
        loaded_dataset = self.model.session.query(model.Dataset).filter(model.Dataset.id == dataset.id).one()
        assert loaded_dataset.job_id == job.id

    def test_jobs(self):
        u = model.User(email="jobtest@foo.bar.baz", password="password")
        job = model.Job()
        job.user = u
        job.tool_id = "cat1"

        self.persist(u, job)

        loaded_job = self.model.session.query(model.Job).filter(model.Job.user == u).first()
        assert loaded_job.tool_id == "cat1"

    def test_job_metrics(self):
        u = model.User(email="jobtest@foo.bar.baz", password="password")
        job = model.Job()
        job.user = u
        job.tool_id = "cat1"

        job.add_metric("gx", "galaxy_slots", 5)
        job.add_metric("system", "system_name", "localhost")

        self.persist(u, job)

        task = model.Task(job=job, working_directory="/tmp", prepare_files_cmd="split.sh")
        task.add_metric("gx", "galaxy_slots", 5)
        task.add_metric("system", "system_name", "localhost")

        big_value = ":".join("%d" % i for i in range(2000))
        task.add_metric("env", "BIG_PATH", big_value)
        self.persist(task)
        # Ensure big values truncated
        assert len(task.text_metrics[1].metric_value) <= 1023

    def test_tasks(self):
        u = model.User(email="jobtest@foo.bar.baz", password="password")
        job = model.Job()
        task = model.Task(job=job, working_directory="/tmp", prepare_files_cmd="split.sh")
        job.user = u
        self.persist(u, job, task)

        loaded_task = self.model.session.query(model.Task).filter(model.Task.job == job).first()
        assert loaded_task.prepare_input_files_cmd == "split.sh"

    def test_history_contents(self):
        u = model.User(email="contents@foo.bar.baz", password="password")
        # gs = model.GalaxySession()
        h1 = model.History(name="HistoryContentsHistory1", user=u)

        self.persist(u, h1, expunge=False)

        d1 = self.new_hda(h1, name="1")
        d2 = self.new_hda(h1, name="2", visible=False)
        d3 = self.new_hda(h1, name="3", deleted=True)
        d4 = self.new_hda(h1, name="4", visible=False, deleted=True)

        self.session().flush()

        def contents_iter_names(**kwds):
            history = (
                self.model.context.query(model.History).filter(model.History.name == "HistoryContentsHistory1").first()
            )
            return list(map(lambda hda: hda.name, history.contents_iter(**kwds)))

        self.assertEqual(contents_iter_names(), ["1", "2", "3", "4"])
        assert contents_iter_names(deleted=False) == ["1", "2"]
        assert contents_iter_names(visible=True) == ["1", "3"]
        assert contents_iter_names(visible=False) == ["2", "4"]
        assert contents_iter_names(deleted=True, visible=False) == ["4"]

        assert contents_iter_names(ids=[d1.id, d2.id, d3.id, d4.id]) == ["1", "2", "3", "4"]
        assert contents_iter_names(ids=[d1.id, d2.id, d3.id, d4.id], max_in_filter_length=1) == ["1", "2", "3", "4"]

        assert contents_iter_names(ids=[d1.id, d3.id]) == ["1", "3"]

    def test_history_audit(self):
        u = model.User(email="contents@foo.bar.baz", password="password")
        h1 = model.History(name="HistoryAuditHistory", user=u)
        h2 = model.History(name="HistoryAuditHistory", user=u)

        def get_audit_table_entries(history):
            return (
                self.session()
                .query(model.HistoryAudit.table)
                .filter(model.HistoryAudit.table.c.history_id == history.id)
                .all()
            )

        def get_latest_entry(entries):
            # key ensures result is correct if new columns are added
            return max(entries, key=lambda x: x.update_time)

        self.persist(u, h1, h2, expunge=False)
        assert len(get_audit_table_entries(h1)) == 1
        assert len(get_audit_table_entries(h2)) == 1

        self.new_hda(h1, name="1")
        self.new_hda(h2, name="2")
        self.session().flush()
        # _next_hid modifies history, plus trigger on HDA means 2 additional audit rows per history

        h1_audits = get_audit_table_entries(h1)
        h2_audits = get_audit_table_entries(h2)
        assert len(h1_audits) == 3
        assert len(h2_audits) == 3

        h1_latest = get_latest_entry(h1_audits)
        h2_latest = get_latest_entry(h2_audits)

        model.HistoryAudit.prune(self.session())

        h1_audits = get_audit_table_entries(h1)
        h2_audits = get_audit_table_entries(h2)
        assert len(h1_audits) == 1
        assert len(h2_audits) == 1
        assert h1_audits[0] == h1_latest
        assert h2_audits[0] == h2_latest

    def _non_empty_flush(self):
        lf = model.LibraryFolder(name="RootFolder")
        session = self.session()
        session.add(lf)
        session.flush()

    def test_flush_refreshes(self):
        # Normally I don't believe in unit testing library code, but the behaviors around attribute
        # states and flushing in SQL Alchemy is very subtle and it is good to have a executable
        # reference for how it behaves in the context of Galaxy objects.
        model = self.model
        user = model.User(email="testworkflows@bx.psu.edu", password="password")
        galaxy_session = model.GalaxySession()
        galaxy_session_other = model.GalaxySession()
        galaxy_session.user = user
        galaxy_session_other.user = user
        self.persist(user, galaxy_session_other, galaxy_session)
        galaxy_session_id = galaxy_session.id

        self.expunge()
        session = self.session()
        galaxy_model_object = self.query(model.GalaxySession).get(galaxy_session_id)
        expected_id = galaxy_model_object.id

        # id loaded as part of the object query, could be any non-deferred attribute.
        assert "id" not in inspect(galaxy_model_object).unloaded

        # Perform an empty flush, verify empty flush doesn't reload all attributes.
        session.flush()
        assert "id" not in inspect(galaxy_model_object).unloaded

        # However, flushing anything non-empty - even unrelated object will invalidate
        # the session ID.
        self._non_empty_flush()
        assert "id" in inspect(galaxy_model_object).unloaded

        # Fetch the ID loads the value from the database
        assert expected_id == galaxy_model_object.id
        assert "id" not in inspect(galaxy_model_object).unloaded

        # Using cached_id instead does not exhibit this behavior.
        self._non_empty_flush()
        assert expected_id == galaxy.model.cached_id(galaxy_model_object)
        assert "id" in inspect(galaxy_model_object).unloaded

        # Keeping the following failed experiments here for future reference,
        # I probed the internals of the attribute tracking and couldn't find an
        # alternative, generalized way to get the previously loaded value for unloaded
        # attributes.
        # print(galaxy_model_object._sa_instance_state.attrs.id)
        # print(dir(galaxy_model_object._sa_instance_state.attrs.id))
        # print(galaxy_model_object._sa_instance_state.attrs.id.loaded_value)
        # print(galaxy_model_object._sa_instance_state.attrs.id.state)
        # print(galaxy_model_object._sa_instance_state.attrs.id.load_history())
        # print(dir(galaxy_model_object._sa_instance_state.attrs.id.load_history()))
        # print(galaxy_model_object._sa_instance_state.identity)
        # print(dir(galaxy_model_object._sa_instance_state))
        # print(galaxy_model_object._sa_instance_state.expired_attributes)
        # print(galaxy_model_object._sa_instance_state.expired)
        # print(galaxy_model_object._sa_instance_state._instance_dict().keys())
        # print(dir(galaxy_model_object._sa_instance_state._instance_dict))
        # assert False

        # Verify cached_id works even immediately after an initial flush, prevents a second SELECT
        # query that would be executed if object.id was used.
        galaxy_model_object_new = model.GalaxySession()
        session.add(galaxy_model_object_new)
        session.flush()
        assert galaxy.model.cached_id(galaxy_model_object_new)
        assert "id" in inspect(galaxy_model_object_new).unloaded

        # Verify a targeted flush prevent expiring unrelated objects.
        galaxy_model_object_new.id
        assert "id" not in inspect(galaxy_model_object_new).unloaded
        session.flush(model.GalaxySession())
        assert "id" not in inspect(galaxy_model_object_new).unloaded

    def test_workflows(self):
        user = model.User(email="testworkflows@bx.psu.edu", password="password")

        def workflow_from_steps(steps):
            stored_workflow = model.StoredWorkflow()
            add_object_to_object_session(stored_workflow, user)
            stored_workflow.user = user
            workflow = model.Workflow()

            if steps:
                for step in steps:
                    if get_object_session(step):
                        add_object_to_object_session(workflow, step)
                        break

            workflow.steps = steps
            workflow.stored_workflow = stored_workflow
            return workflow

        child_workflow = workflow_from_steps([])
        self.persist(child_workflow)

        workflow_step_1 = model.WorkflowStep()
        workflow_step_1.order_index = 0
        workflow_step_1.type = "data_input"
        workflow_step_2 = model.WorkflowStep()
        workflow_step_2.order_index = 1
        workflow_step_2.type = "subworkflow"
        add_object_to_object_session(workflow_step_2, child_workflow)
        workflow_step_2.subworkflow = child_workflow

        workflow_step_1.get_or_add_input("moo1")
        workflow_step_1.get_or_add_input("moo2")
        workflow_step_2.get_or_add_input("moo")
        workflow_step_1.add_connection("foo", "cow", workflow_step_2)

        workflow = workflow_from_steps([workflow_step_1, workflow_step_2])
        self.persist(workflow)
        workflow_id = workflow.id

        annotation = model.WorkflowStepAnnotationAssociation()
        annotation.annotation = "Test Step Annotation"
        annotation.user = user
        add_object_to_object_session(annotation, workflow_step_1)
        annotation.workflow_step = workflow_step_1
        self.persist(annotation)

        assert workflow_step_1.id is not None
        h1 = model.History(name="WorkflowHistory1", user=user)

        invocation_uuid = uuid.uuid1()

        workflow_invocation = model.WorkflowInvocation()
        workflow_invocation.uuid = invocation_uuid
        add_object_to_object_session(workflow_invocation, h1)
        workflow_invocation.history = h1

        workflow_invocation_step1 = model.WorkflowInvocationStep()
        add_object_to_object_session(workflow_invocation_step1, workflow_invocation)
        workflow_invocation_step1.workflow_invocation = workflow_invocation
        workflow_invocation_step1.workflow_step = workflow_step_1

        subworkflow_invocation = model.WorkflowInvocation()
        workflow_invocation.attach_subworkflow_invocation_for_step(workflow_step_2, subworkflow_invocation)

        workflow_invocation_step2 = model.WorkflowInvocationStep()
        add_object_to_object_session(workflow_invocation_step2, workflow_invocation)
        workflow_invocation_step2.workflow_invocation = workflow_invocation
        workflow_invocation_step2.workflow_step = workflow_step_2

        workflow_invocation.workflow = workflow

        d1 = self.new_hda(h1, name="1")
        workflow_request_dataset = model.WorkflowRequestToInputDatasetAssociation()
        add_object_to_object_session(workflow_request_dataset, workflow_invocation)
        workflow_request_dataset.workflow_invocation = workflow_invocation
        workflow_request_dataset.workflow_step = workflow_step_1
        workflow_request_dataset.dataset = d1
        self.persist(workflow_invocation)
        assert workflow_request_dataset is not None
        assert workflow_invocation.id is not None

        history_id = h1.id
        self.expunge()

        loaded_invocation = self.query(model.WorkflowInvocation).get(workflow_invocation.id)
        assert loaded_invocation.uuid == invocation_uuid, f"{loaded_invocation.uuid} != {invocation_uuid}"
        assert loaded_invocation
        assert loaded_invocation.history.id == history_id

        step_1, step_2 = loaded_invocation.workflow.steps

        assert not step_1.subworkflow
        assert step_2.subworkflow
        assert len(loaded_invocation.steps) == 2

        subworkflow_invocation_assoc = loaded_invocation.get_subworkflow_invocation_association_for_step(step_2)
        assert subworkflow_invocation_assoc is not None
        assert isinstance(subworkflow_invocation_assoc.subworkflow_invocation, model.WorkflowInvocation)
        assert isinstance(subworkflow_invocation_assoc.parent_workflow_invocation, model.WorkflowInvocation)

        assert subworkflow_invocation_assoc.subworkflow_invocation.history.id == history_id

        loaded_workflow = self.query(model.Workflow).get(workflow_id)
        assert len(loaded_workflow.steps[0].annotations) == 1
        copied_workflow = loaded_workflow.copy(user=user)
        annotations = copied_workflow.steps[0].annotations
        assert len(annotations) == 1

    def test_role_creation(self):
        security_agent = GalaxyRBACAgent(self.model)

        def check_private_role(private_role, email):
            assert private_role.type == model.Role.types.PRIVATE
            assert len(private_role.users) == 1
            assert private_role.name == email
            assert private_role.description == "Private Role for " + email

        email = "rule_user_1@example.com"
        u = model.User(email=email, password="password")
        self.persist(u)

        role = security_agent.get_private_user_role(u)
        assert role is None
        role = security_agent.create_private_user_role(u)
        assert role is not None
        check_private_role(role, email)

        email = "rule_user_2@example.com"
        u = model.User(email=email, password="password")
        self.persist(u)
        role = security_agent.get_private_user_role(u)
        assert role is None
        role = security_agent.get_private_user_role(u, auto_create=True)
        assert role is not None
        check_private_role(role, email)

        # make sure re-running auto_create doesn't break things
        role = security_agent.get_private_user_role(u, auto_create=True)
        assert role is not None
        check_private_role(role, email)

    def test_private_share_role(self):
        security_agent = GalaxyRBACAgent(self.model)

        u_from, u_to, u_other = self._three_users("private_share_role")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        security_agent.privately_share_dataset(d1.dataset, [u_to])
        assert security_agent.can_access_dataset(u_to.all_roles(), d1.dataset)
        assert not security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_make_dataset_public(self):
        security_agent = GalaxyRBACAgent(self.model)
        u_from, u_to, u_other = self._three_users("make_dataset_public")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        security_agent.privately_share_dataset(d1.dataset, [u_to])

        security_agent.make_dataset_public(d1.dataset)
        assert security_agent.can_access_dataset(u_to.all_roles(), d1.dataset)
        assert security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_set_all_dataset_permissions(self):
        security_agent = GalaxyRBACAgent(self.model)
        u_from, _, u_other = self._three_users("set_all_perms")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        role = security_agent.get_private_user_role(u_from, auto_create=True)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {access_action: [role], manage_action: [role]}
        assert security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)
        security_agent.set_all_dataset_permissions(d1.dataset, permissions)
        assert not security_agent.allow_action(
            u_other.all_roles(), security_agent.permitted_actions.DATASET_ACCESS, d1.dataset
        )
        assert not security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_can_manage_privately_shared_dataset(self):
        security_agent = GalaxyRBACAgent(self.model)
        u_from, u_to, u_other = self._three_users("can_manage_dataset")

        h = model.History(name="History for Prevent Sharing", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        self._make_owned(security_agent, u_from, d1)
        assert security_agent.can_manage_dataset(u_from.all_roles(), d1.dataset)
        security_agent.privately_share_dataset(d1.dataset, [u_to])
        assert not security_agent.can_manage_dataset(u_to.all_roles(), d1.dataset)

    def test_can_manage_private_dataset(self):
        security_agent = GalaxyRBACAgent(self.model)
        u_from, _, u_other = self._three_users("can_manage_dataset_ps")

        h = model.History(name="History for Prevent Sharing", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        self._make_private(security_agent, u_from, d1)
        assert security_agent.can_manage_dataset(u_from.all_roles(), d1.dataset)
        assert not security_agent.can_manage_dataset(u_other.all_roles(), d1.dataset)

    def test_history_hid_counter_is_expired_after_next_hid_call(self):
        u = model.User(email="hid_abuser@example.com", password="password")
        h = model.History(name="History for hid testing", user=u)
        self.persist(u, h)
        state = inspect(h)
        assert h.hid_counter == 1
        assert "hid_counter" not in state.unloaded
        assert "id" not in state.unloaded

        h._next_hid()

        assert "hid_counter" in state.unloaded  # this attribute has been expired
        assert "id" not in state.unloaded  # but other attributes have NOT been expired
        assert h.hid_counter == 2  # check this last: this causes thie hid_counter to be reloaded

    def test_next_hid(self):
        u = model.User(email="hid_abuser@example.com", password="password")
        h = model.History(name="History for hid testing", user=u)
        self.persist(u, h)
        assert h.hid_counter == 1
        h._next_hid()
        assert h.hid_counter == 2
        h._next_hid(n=3)
        assert h.hid_counter == 5

    def _three_users(self, suffix):
        email_from = f"user_{suffix}e1@example.com"
        email_to = f"user_{suffix}e2@example.com"
        email_other = f"user_{suffix}e3@example.com"

        u_from = model.User(email=email_from, password="password")
        u_to = model.User(email=email_to, password="password")
        u_other = model.User(email=email_other, password="password")
        self.persist(u_from, u_to, u_other)
        return u_from, u_to, u_other

    def _make_private(self, security_agent, user, hda):
        role = security_agent.get_private_user_role(user, auto_create=True)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {access_action: [role], manage_action: [role]}
        security_agent.set_all_dataset_permissions(hda.dataset, permissions)

    def _make_owned(self, security_agent, user, hda):
        role = security_agent.get_private_user_role(user, auto_create=True)
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {manage_action: [role]}
        security_agent.set_all_dataset_permissions(hda.dataset, permissions)

    def new_hda(self, history, **kwds):
        return history.add_dataset(
            model.HistoryDatasetAssociation(create_dataset=True, sa_session=self.model.session, **kwds)
        )


@skip_if_not_postgres_base
class PostgresMappingTests(MappingTests):
    @classmethod
    def _db_uri(cls):
        base = os.environ.get("GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE")
        dbname = "gxtest" + str(uuid.uuid4())
        assert base
        postgres_url = base + dbname
        create_database(postgres_url)
        return postgres_url


class MockObjectStore:
    def __init__(self):
        pass

    def size(self, dataset):
        return 42

    def exists(self, *args, **kwds):
        return True

    def get_filename(self, *args, **kwds):
        return "mock_dataset_14.dat"

    def get_store_by(self, *args, **kwds):
        return "id"

    def update_from_file(self, *arg, **kwds):
        pass


def get_suite():
    suite = unittest.TestSuite()
    suite.addTest(MappingTests("test_basic"))
    return suite
