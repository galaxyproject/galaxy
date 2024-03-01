import pytest
from sqlalchemy.exc import IntegrityError

from galaxy import model as m
from galaxy.managers import hdcas as lib
from . import (
    MockTransaction,
    PRIVATE_OBJECT_STORE_ID,
)

# test model definitions


class User:
    def test_username_is_unique(self, make_user):
        make_user(username="a")
        with pytest.raises(IntegrityError):
            make_user(username="a")


# replacing test_galaxy_mapping.py


def test_hda_to_library_dataset_dataset_association(session, make_user, make_history, make_hda, make_library_folder):
    hda = make_hda(create_dataset=True, sa_session=session)
    target_folder = make_library_folder()
    mock_trans = MockTransaction(user=None)

    ldda = hda.to_library_dataset_dataset_association(
        trans=mock_trans,
        target_folder=target_folder,
    )
    assert target_folder.item_count == 1
    assert ldda.id
    assert ldda.library_dataset.id
    assert ldda.library_dataset.library_dataset_dataset_association.id

    new_ldda = hda.to_library_dataset_dataset_association(
        trans=mock_trans, target_folder=target_folder, replace_dataset=ldda.library_dataset
    )
    assert new_ldda.id != ldda.id
    assert new_ldda.library_dataset_id == ldda.library_dataset_id
    assert new_ldda.library_dataset.library_dataset_dataset_association_id == new_ldda.id
    assert len(new_ldda.library_dataset.expired_datasets) == 1
    assert new_ldda.library_dataset.expired_datasets[0] == ldda
    assert target_folder.item_count == 1


def test_hda_to_library_dataset_dataset_association_fails_if_private(
    session, make_user, make_history, make_hda, make_library_folder
):
    hda = make_hda(create_dataset=True, sa_session=session)
    hda.dataset.object_store_id = PRIVATE_OBJECT_STORE_ID
    target_folder = make_library_folder()
    mock_trans = MockTransaction(user=None)

    with pytest.raises(Exception) as exec_info:
        hda.to_library_dataset_dataset_association(
            trans=mock_trans,
            target_folder=target_folder,
        )
    assert m.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE in str(exec_info.value)


def test_collection_get_interface(session, make_hda, make_dataset_collection):
    c = make_dataset_collection(collection_type="list")
    d = make_hda(create_dataset=True, sa_session=session)
    elements = 100
    dces = [
        m.DatasetCollectionElement(collection=c, element=d, element_identifier=f"{i}", element_index=i)
        for i in range(elements)
    ]
    for i in range(elements):
        assert c[i] == dces[i]


def test_collections_in_histories(session, make_dataset_collection, make_dataset_collection_element, make_hdca):
    c = make_dataset_collection(collection_type="pair")
    dce1 = make_dataset_collection_element(collection=c, element_identifier="left")
    dce2 = make_dataset_collection_element(collection=c, element_identifier="right")
    make_hdca(name="foo", collection=c)
    loaded_dataset_collection = lib.get_hdca_by_name(session, "foo").collection

    assert len(loaded_dataset_collection.elements) == 2
    assert loaded_dataset_collection.collection_type == "pair"
    assert loaded_dataset_collection["left"] == dce1
    assert loaded_dataset_collection["right"] == dce2


def test_dataset_action_tuples(
    session,
    make_user,
    make_history,
    make_hda,
    make_role,
    make_dataset_permissions,
    make_dataset_collection,
    make_dataset_collection_element,
):
    role = make_role()
    hda1 = make_hda(create_dataset=True, sa_session=session)
    hda2 = make_hda(create_dataset=True, sa_session=session)
    make_dataset_permissions(action="action1", dataset=hda1.dataset, role=role)
    make_dataset_permissions(action=None, dataset=hda1.dataset, role=role)
    make_dataset_permissions(action="action3", dataset=hda1.dataset, role=role)
    c = make_dataset_collection(collection_type="type1")
    make_dataset_collection_element(collection=c, element=hda1)
    make_dataset_collection_element(collection=c, element=hda2)
    assert c.dataset_action_tuples == [("action1", role.id), ("action3", role.id)]


def test_dataset_dbkeys_and_extensions_summary(
    session, make_hda, make_dataset_collection, make_dataset_collection_element, make_hdca
):
    d1 = make_hda(extension="bam", dbkey="hg19", create_dataset=True, sa_session=session)
    d2 = make_hda(extension="txt", dbkey="hg19", create_dataset=True, sa_session=session)
    c1 = make_dataset_collection(collection_type="paired")
    make_dataset_collection_element(collection=c1, element=d1)
    make_dataset_collection_element(collection=c1, element=d2)

    hdca = make_hdca(collection=c1)
    assert hdca.dataset_dbkeys_and_extensions_summary[0] == {"hg19"}
    assert hdca.dataset_dbkeys_and_extensions_summary[1] == {"bam", "txt"}


def test_populated_optimized_ok(session, make_dataset_collection, make_dataset_collection_element, make_hda):
    c1 = make_dataset_collection(collection_type="paired")
    make_dataset_collection_element(collection=c1, element=make_hda(create_dataset=True, sa_session=session))
    make_dataset_collection_element(collection=c1, element=make_hda(create_dataset=True, sa_session=session))
    assert c1.populated
    assert c1.populated_optimized


def test_populated_optimized_empty_list_list_ok(session, make_dataset_collection, make_dataset_collection_element):
    c1 = make_dataset_collection(collection_type="list")
    c2 = make_dataset_collection(collection_type="list:list")
    make_dataset_collection_element(collection=c2, element=c1)
    assert c1.populated
    assert c1.populated_optimized
    assert c2.populated
    assert c2.populated_optimized


def test_populated_optimized_list_list_not_populated(session, make_dataset_collection, make_dataset_collection_element):
    c1 = make_dataset_collection(collection_type="list", populated=False)
    c2 = make_dataset_collection(collection_type="list:list")
    make_dataset_collection_element(collection=c2, element=c1)
    assert not c1.populated
    assert not c1.populated_optimized
    assert not c2.populated
    assert not c2.populated_optimized


def test_default_disk_usage(session, make_user):
    u = make_user()
    u.adjust_total_disk_usage(1, None)
    user_reload = session.get(m.User, u.id)
    assert user_reload.disk_usage == 1
