import random
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)

import galaxy.model.mapping as mapping


def test_APIKeys(model, session, user):
    cls = model.APIKeys
    assert cls.__tablename__ == 'api_keys'
    with dbcleanup(session, cls):
        create_time, user_id, key = datetime.now(), user.id, get_random_string()
        obj = cls(user_id=user_id, key=key, create_time=create_time)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.user_id == user_id
        assert stored_obj.key == key
        # test mapped relationships
        assert stored_obj.user.id == user.id


def test_CloudAuthz(model, session, user, user_authnz_token):
    cls = model.CloudAuthz
    assert cls.__tablename__ == 'cloudauthz'
    with dbcleanup(session, cls):
        provider, config, description = 'a', 'b', 'c'
        obj = cls(user.id, provider, config, user_authnz_token.id, description)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.provider == provider
        assert stored_obj.config == config
        assert stored_obj.authn_id == user_authnz_token.id
        assert stored_obj.tokens is None
        assert stored_obj.last_update
        assert stored_obj.last_activity
        assert stored_obj.description == description
        assert stored_obj.create_time
        # test mapped relationships
        assert stored_obj.user.id == user.id
        assert stored_obj.authn.id == user_authnz_token.id


def test_CustosAuthnzToken(model, session, user):
    cls = model.CustosAuthnzToken
    assert cls.__tablename__ == 'custos_authnz_token'
    assert has_unique_constraint(cls.__table__, ('user_id', 'external_user_id', 'provider'))
    assert has_unique_constraint(cls.__table__, ('external_user_id', 'provider'))
    with dbcleanup(session, cls):
        external_user_id = get_random_string()
        provider = get_random_string()
        access_token = 'c'
        id_token = 'd'
        refresh_token = 'e'
        expiration_time = datetime.now()
        refresh_expiration_time = datetime.now()
        obj = cls(user, external_user_id, provider, access_token, id_token, refresh_token,
            expiration_time, refresh_expiration_time)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.external_user_id == external_user_id
        assert stored_obj.provider == provider
        assert stored_obj.access_token == access_token
        assert stored_obj.id_token == id_token
        assert stored_obj.refresh_token == refresh_token
        assert stored_obj.expiration_time == expiration_time
        assert stored_obj.refresh_expiration_time == refresh_expiration_time
        # test mapped relationships
        assert stored_obj.user.id == user.id


def test_DatasetHash(model, session, dataset):
    cls = model.DatasetHash
    assert cls.__tablename__ == 'dataset_hash'
    with dbcleanup(session, cls):
        hash_function, hash_value, extra_files_path = 'a', 'b', 'c'
        obj = cls()
        obj.dataset = dataset
        obj.hash_function = hash_function
        obj.hash_value = hash_value
        obj.extra_files_path = extra_files_path
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.dataset_id == dataset.id
        assert stored_obj.hash_function == hash_function
        assert stored_obj.hash_value == hash_value
        assert stored_obj.extra_files_path == extra_files_path
        # test mapped relationships
        assert stored_obj.dataset.id == dataset.id


def test_DatasetSource(model, session, dataset, dataset_source_hash):
    cls = model.DatasetSource
    assert cls.__tablename__ == 'dataset_source'
    with dbcleanup(session, cls):
        source_uri, extra_files_path, transform = 'a', 'b', 'c'
        obj = cls()
        obj.dataset = dataset
        obj.source_uri = source_uri
        obj.extra_files_path = extra_files_path
        obj.transform = transform
        obj.hashes.append(dataset_source_hash)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.dataset_id == dataset.id
        assert stored_obj.source_uri == source_uri
        assert stored_obj.extra_files_path == extra_files_path
        assert stored_obj.transform == transform
        # test mapped relationships
        assert stored_obj.dataset.id == dataset.id
        assert stored_obj.hashes == [dataset_source_hash]


def test_DatasetSourceHash(model, session, dataset_source):
    cls = model.DatasetSourceHash
    assert cls.__tablename__ == 'dataset_source_hash'
    with dbcleanup(session, cls):
        hash_function, hash_value = 'a', 'b'
        obj = cls()
        obj.source = dataset_source
        obj.hash_function = hash_function
        obj.hash_value = hash_value
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.dataset_source_id == dataset_source.id
        assert stored_obj.hash_function == hash_function
        assert stored_obj.hash_value == hash_value
        # test mapped relationships
        assert stored_obj.source.id == dataset_source.id


def test_DatasetPermissions(model, session, dataset, role):
    cls = model.DatasetPermissions
    assert cls.__tablename__ == 'dataset_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, dataset, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.action == action
        assert stored_obj.dataset_id == dataset.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.dataset == dataset
        assert stored_obj.role == role


def test_DefaultHistoryPermissions(model, session, history, role):
    cls = model.DefaultHistoryPermissions
    assert cls.__tablename__ == 'default_history_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(history, action, role)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.action == action
        assert stored_obj.history_id == history.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.history.id == history.id
        assert stored_obj.role == role


def test_DefaultQuotaAssociation(model, session, quota):
    cls = model.DefaultQuotaAssociation
    assert cls.__tablename__ == 'default_quota_association'
    with dbcleanup(session, cls):
        type = cls.types.REGISTERED
        obj = cls(type, quota)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.type == type
        assert stored_obj.quota_id == quota.id
        # test mapped relationships
        assert stored_obj.quota.id == quota.id


def test_DefaultUserPermissions(model, session, user, role):
    cls = model.DefaultUserPermissions
    assert cls.__tablename__ == 'default_user_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(user, action, role)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.action == action
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.user.id == user.id
        assert stored_obj.role.id == role.id


def test_DynamicTool(model, session, workflow_step):
    cls = model.DynamicTool
    assert cls.__tablename__ == 'dynamic_tool'
    with dbcleanup(session, cls):
        tool_format = 'a'
        tool_id = 'b'
        tool_version = 'c'
        tool_path = 'd'
        tool_directory = 'e'
        uuid = None
        active = True
        hidden = True
        value = 'f'
        obj = cls(tool_format, tool_id, tool_version, tool_path, tool_directory, uuid,
                active, hidden, value)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.workflow_steps.append(workflow_step)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.uuid
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.tool_id == tool_id
        assert stored_obj.tool_version == tool_version
        assert stored_obj.tool_format == tool_format
        assert stored_obj.tool_path == tool_path
        assert stored_obj.tool_directory == tool_directory
        assert stored_obj.hidden == hidden
        assert stored_obj.active == active
        assert stored_obj.value == value
        # test mapped relationships
        assert workflow_step in stored_obj.workflow_steps


def test_FormDefinition(model, session, form_definition_current):
    cls = model.FormDefinition
    assert cls.__tablename__ == 'form_definition'
    with dbcleanup(session, cls):
        name, desc, fields, type, layout = 'a', 'b', 'c', 'd', 'e'
        obj = cls()
        obj.name = name
        obj.desc = desc
        obj.form_definition_current = form_definition_current
        obj.fields = fields
        obj.type = type
        obj.layout = layout
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.name == name
        assert stored_obj.desc == desc
        assert stored_obj.form_definition_current_id == form_definition_current.id
        assert stored_obj.fields == fields
        assert stored_obj.type == type
        assert stored_obj.layout == layout
        # test mapped relationships
        assert stored_obj.form_definition_current.id == form_definition_current.id


def test_FormDefinitionCurrent(model, session, form_definition):
    cls = model.FormDefinitionCurrent
    assert cls.__tablename__ == 'form_definition_current'
    with dbcleanup(session, cls):
        obj = cls()
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        deleted = True
        obj.create_time = create_time
        obj.update_time = update_time
        obj.latest_form = form_definition
        obj.deleted = deleted
        obj.forms.append(form_definition)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.latest_form_id == form_definition.id
        assert stored_obj.deleted == deleted
        # test mapped relationships
        assert stored_obj.latest_form.id == form_definition.id
        assert stored_obj.forms == [form_definition]


def test_FormValues(model, session, form_definition):
    cls = model.FormValues
    assert cls.__tablename__ == 'form_values'
    with dbcleanup(session, cls):
        content = 'a'
        obj = cls()
        obj.form_definition = form_definition
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.content = content
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.content == content
        assert stored_obj.form_definition_id == form_definition.id
        # test mapped relationships
        assert stored_obj.form_definition.id == form_definition.id


def test_GroupQuotaAssociation(model, session, group, quota):
    cls = model.GroupQuotaAssociation
    assert cls.__tablename__ == 'group_quota_association'
    with dbcleanup(session, cls):
        obj = cls(group, quota)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.group_id == group.id
        assert stored_obj.quota_id == quota.id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        # test mapped relationships
        assert stored_obj.group.id == group.id
        assert stored_obj.quota.id == quota.id


def test_GroupRoleAssociation(model, session, group, role):
    cls = model.GroupRoleAssociation
    assert cls.__tablename__ == 'group_role_association'
    with dbcleanup(session, cls):
        obj = cls(group, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.group_id == group.id
        assert stored_obj.role_id == role.id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        # test mapped relationships
        assert stored_obj.group.id == group.id
        assert stored_obj.role.id == role.id


def test_HistoryAudit(model, session, history):
    cls = model.HistoryAudit
    assert cls.__tablename__ == 'history_audit'
    with dbcleanup(session, cls):
        update_time = datetime.now()
        obj = cls(history, update_time)
        persist(session, obj, return_id=False)

        stmt = select(cls).where(cls.history_id == history.id, cls.update_time == update_time)
        stored_obj = get_stored_obj(session, cls, stmt=stmt)
        # test mapped columns
        assert stored_obj.history_id == history.id
        assert stored_obj.update_time == update_time
        # test mapped relationships
        assert stored_obj.history.id == history.id


def test_HistoryAnnotationAssociation(model, session, history, user):
    cls = model.HistoryAnnotationAssociation
    assert cls.__tablename__ == 'history_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.history = history
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_id == history.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.history.id == history.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetAssociationAnnotationAssociation(
        model, session, history_dataset_association, user):
    cls = model.HistoryDatasetAssociationAnnotationAssociation
    assert cls.__tablename__ == 'history_dataset_association_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.hda = history_dataset_association
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_association_id == history_dataset_association.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.hda.id == history_dataset_association.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetAssociationRatingAssociation(model, session, history_dataset_association, user):
    cls = model.HistoryDatasetAssociationRatingAssociation
    assert cls.__tablename__ == 'history_dataset_association_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history_dataset_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_association_id == history_dataset_association.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.history_dataset_association.id == history_dataset_association.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetAssociationTagAssociation(
        model, session, history_dataset_association, tag, user):
    cls = model.HistoryDatasetAssociationTagAssociation
    assert cls.__tablename__ == 'history_dataset_association_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history_dataset_association_id = history_dataset_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_association_id == history_dataset_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.history_dataset_association.id == history_dataset_association.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetCollectionAssociationAnnotationAssociation(
        model, session, history_dataset_collection_association, user):
    cls = model.HistoryDatasetCollectionAssociationAnnotationAssociation
    assert cls.__tablename__ == 'history_dataset_collection_annotation_association'
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.history_dataset_collection = history_dataset_collection_association
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.history_dataset_collection.id == history_dataset_collection_association.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetCollectionRatingAssociation(
        model, session, history_dataset_collection_association, user):
    cls = model.HistoryDatasetCollectionRatingAssociation
    assert cls.__tablename__ == 'history_dataset_collection_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history_dataset_collection_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
        assert stored_obj.user.id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.dataset_collection.id == history_dataset_collection_association.id
        assert stored_obj.user.id == user.id


def test_HistoryDatasetCollectionTagAssociation(model, session, history_dataset_collection_association, tag, user):
    cls = model.HistoryDatasetCollectionTagAssociation
    assert cls.__tablename__ == 'history_dataset_collection_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history_dataset_collection_id = history_dataset_collection_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.dataset_collection.id == history_dataset_collection_association.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_HistoryRatingAssociation(model, session, history, user):
    cls = model.HistoryRatingAssociation
    assert cls.__tablename__ == 'history_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_id == history.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.history.id == history.id
        assert stored_obj.user.id == user.id


def test_HistoryTagAssociation(model, session, history, tag, user):
    cls = model.HistoryTagAssociation
    assert cls.__tablename__ == 'history_tag_association'

    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history_id = history.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.history_id == history.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.history.id == history.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_JobToInputDatasetCollectionAssociation(
        model, session, history_dataset_collection_association, job):
    cls = model.JobToInputDatasetCollectionAssociation
    assert cls.__tablename__ == 'job_to_input_dataset_collection'

    with dbcleanup(session, cls):
        name = 'a'
        obj = cls(name, history_dataset_collection_association)
        obj.job = job
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.job_id == job.id
        assert stored_obj.dataset_collection_id == history_dataset_collection_association.id
        assert stored_obj.name == name
        # test mapped relationships
        assert stored_obj.job.id == job.id
        assert stored_obj.dataset_collection.id == history_dataset_collection_association.id


def test_JobToInputDatasetCollectionElementAssociation(
        model, session, dataset_collection_element, job):
    cls = model.JobToInputDatasetCollectionElementAssociation
    assert cls.__tablename__ == 'job_to_input_dataset_collection_element'

    with dbcleanup(session, cls):
        name = 'a'
        obj = cls(name, dataset_collection_element)
        obj.job = job
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.job_id == job.id
        assert stored_obj.dataset_collection_element_id == dataset_collection_element.id
        assert stored_obj.name == name
        # test mapped relationships
        assert stored_obj.job.id == job.id
        assert stored_obj.dataset_collection_element.id == dataset_collection_element.id


def test_JobToInputDatasetAssociation(model, session, history_dataset_association, job):
    cls = model.JobToInputDatasetAssociation
    assert cls.__tablename__ == 'job_to_input_dataset'

    with dbcleanup(session, cls):
        name, dataset_version = 'a', 9
        obj = cls(name, history_dataset_association)
        obj.history_dataset_association_id = history_dataset_association.id
        obj.job = job
        obj.dataset_version = dataset_version
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.job_id == job.id
        assert stored_obj.dataset_id == history_dataset_association.id
        assert stored_obj.dataset_version == dataset_version
        assert stored_obj.name == name
        # test mapped relationships
        assert stored_obj.job.id == job.id
        assert stored_obj.dataset.id == history_dataset_association.id


def test_Library(model, session, library_folder, library_permission):
    cls = model.Library
    assert cls.__tablename__ == 'library'
    with dbcleanup(session, cls):
        name, deleted, purged, description, synopsis = 'a', True, True, 'b', 'c'
        obj = cls(name, description, synopsis, library_folder)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.deleted = deleted
        obj.purged = purged
        obj.actions.append(library_permission)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.root_folder_id == library_folder.id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.name == name
        assert stored_obj.deleted == deleted
        assert stored_obj.purged == purged
        assert stored_obj.description == description
        assert stored_obj.synopsis == synopsis
        # test mapped relationships
        assert stored_obj.root_folder.id == library_folder.id
        assert stored_obj.actions == [library_permission]


def test_LibraryDatasetCollectionAnnotationAssociation(
        model, session, library_dataset_collection_association, user):
    cls = model.LibraryDatasetCollectionAnnotationAssociation
    assert cls.__tablename__ == 'library_dataset_collection_annotation_association'
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.dataset_collection = library_dataset_collection_association
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
        assert stored_obj.user.id == user.id


def test_LibraryDatasetCollectionTagAssociation(model, session, library_dataset_collection_association, tag, user):
    cls = model.LibraryDatasetCollectionTagAssociation
    assert cls.__tablename__ == 'library_dataset_collection_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.library_dataset_collection_id = library_dataset_collection_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_LibraryDatasetCollectionRatingAssociation(
        model, session, library_dataset_collection_association, user):
    cls = model.LibraryDatasetCollectionRatingAssociation
    assert cls.__tablename__ == 'library_dataset_collection_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, library_dataset_collection_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
        assert stored_obj.user.id == user.id


def test_LibraryDatasetDatasetAssociationPermissions(
        model, session, library_dataset_dataset_association, role):
    cls = model.LibraryDatasetDatasetAssociationPermissions
    assert cls.__tablename__ == 'library_dataset_dataset_association_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, library_dataset_dataset_association, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.action == action
        assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
        assert stored_obj.role.id == role.id


def test_LibraryDatasetDatasetAssociationTagAssociation(
        model, session, library_dataset_dataset_association, tag, user):
    cls = model.LibraryDatasetDatasetAssociationTagAssociation
    assert cls.__tablename__ == 'library_dataset_dataset_association_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.library_dataset_dataset_association_id = library_dataset_dataset_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_LibraryDatasetPermissions(model, session, library_dataset, role):
    cls = model.LibraryDatasetPermissions
    assert cls.__tablename__ == 'library_dataset_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, library_dataset, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.action == action
        assert stored_obj.library_dataset_id == library_dataset.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.library_dataset.id == library_dataset.id
        assert stored_obj.role.id == role.id


def test_LibraryFolderPermissions(model, session, library_folder, role):
    cls = model.LibraryFolderPermissions
    assert cls.__tablename__ == 'library_folder_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, library_folder, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.action == action
        assert stored_obj.library_folder_id == library_folder.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.folder.id == library_folder.id
        assert stored_obj.role.id == role.id


def test_LibraryPermissions(model, session, library, role):
    cls = model.LibraryPermissions
    assert cls.__tablename__ == 'library_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, library, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.action == action
        assert stored_obj.library_id == library.id
        assert stored_obj.role_id == role.id
        # test mapped relationships
        assert stored_obj.library.id == library.id
        assert stored_obj.role.id == role.id


def test_Page(
        model,
        session,
        user,
        page_revision,
        page_tag_association,
        page_annotation_association,
        page_rating_association,
        page_user_share_association,
):
    cls = model.Page
    assert cls.__tablename__ == 'page'
    assert has_index(cls.__table__, ('slug',))
    with dbcleanup(session, cls):
        title, deleted, importable, slug, published = 'a', True, True, 'b', True
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls()
        obj.user = user
        obj.title = title
        obj.deleted = deleted
        obj.importable = importable
        obj.slug = slug
        obj.published = published
        obj.create_time = create_time
        obj.update_time = update_time
        # This is OK for this test; however, page_revision.page != obj. Can we do better?
        obj.latest_revision = page_revision
        obj.revisions.append(page_revision)
        obj.tags.append(page_tag_association)
        obj.annotations.append(page_annotation_association)
        obj.ratings.append(page_rating_association)
        obj.users_shared_with.append(page_user_share_association)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.user_id == user.id
        assert stored_obj.latest_revision_id == page_revision.id
        assert stored_obj.title == title
        assert stored_obj.deleted == deleted
        assert stored_obj.importable == importable
        assert stored_obj.slug == slug
        assert stored_obj.published == published
        # This doesn't test the average amount, just the mapping.
        assert stored_obj.average_rating == page_rating_association.rating
        # test mapped relationships
        assert stored_obj.user.id == user.id
        assert stored_obj.revisions == [page_revision]
        assert stored_obj.latest_revision.id == page_revision.id
        assert stored_obj.tags == [page_tag_association]
        assert stored_obj.annotations == [page_annotation_association]
        assert stored_obj.ratings == [page_rating_association]
        assert stored_obj.users_shared_with == [page_user_share_association]


def test_Page_average_rating(model, session, page, user):
    cls = model.PageRatingAssociation
    with dbcleanup(session, cls):
        # Page has been expunged; to access its deferred properties,
        # it needs to be added back to the session.
        session.add(page)
        assert page.average_rating is None  # With no ratings, we expect None.
        # Create ratings
        for rating in (1, 2, 3, 4, 5):
            r = cls(user, page)
            r.rating = rating
            persist(session, r)
        assert page.average_rating == 3.0  # Expect average after ratings added.


def test_PageAnnotationAssociation(model, session, page, user):
    cls = model.PageAnnotationAssociation
    assert cls.__tablename__ == 'page_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.page = page
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.page_id == page.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.page.id == page.id
        assert stored_obj.user.id == user.id


def test_PageRatingAssociation(model, session, page, user):
    cls = model.PageRatingAssociation
    assert cls.__tablename__ == 'page_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, page, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.page_id == page.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.page.id == page.id
        assert stored_obj.user.id == user.id


def test_PageRevision(model, session, page):
    cls = model.PageRevision
    assert cls.__tablename__ == 'page_revision'
    with dbcleanup(session, cls):
        obj = cls()
        obj.page = page
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        title, content = 'a', 'b'
        obj.title = title
        obj.content = content
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.page_id == page.id
        assert stored_obj.title == title
        assert stored_obj.content == content
        assert stored_obj.content_format == model.PageRevision.DEFAULT_CONTENT_FORMAT
        # test mapped relationships
        assert stored_obj.page.id == page.id


def test_PageTagAssociation(model, session, page, tag, user):
    cls = model.PageTagAssociation
    assert cls.__tablename__ == 'page_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.page_id = page.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.page_id == page.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.page.id == page.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_PageUserShareAssociation(model, session, page, user):
    cls = model.PageUserShareAssociation
    assert cls.__tablename__ == 'page_user_share_association'
    with dbcleanup(session, cls):
        obj = cls()
        obj.page = page
        obj.user = user
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.page_id == page.id
        assert stored_obj.user_id == user.id
        # test mapped relationships
        assert stored_obj.page.id == page.id
        assert stored_obj.user.id == user.id


def test_PasswordResetToken(model, session, user):
    cls = model.PasswordResetToken
    assert cls.__tablename__ == 'password_reset_token'
    with dbcleanup(session, cls):
        token = get_random_string()
        expiration_time = datetime.now()
        obj = cls(user, token)
        obj.expiration_time = expiration_time
        persist(session, obj, return_id=False)

        stmt = select(cls).where(cls.token == token)
        stored_obj = get_stored_obj(session, cls, stmt=stmt)
        # test mapped columns
        assert stored_obj.token == token
        assert stored_obj.expiration_time == expiration_time
        # test mapped relationships
        assert stored_obj.user.id == user.id


def test_PSAAssociation(model, session):
    cls = model.PSAAssociation
    assert cls.__tablename__ == 'psa_association'
    with dbcleanup(session, cls):
        server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
        obj = cls(server_url, handle, secret, issued, lifetime, assoc_type)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.server_url == server_url
        assert stored_obj.handle == handle
        assert stored_obj.secret == secret
        assert stored_obj.issued == issued
        assert stored_obj.lifetime == lifetime
        assert stored_obj.assoc_type == assoc_type


def test_PSACode(model, session):
    cls = model.PSACode
    assert cls.__tablename__ == 'psa_code'
    assert has_unique_constraint(cls.__table__, ('code', 'email'))
    with dbcleanup(session, cls):
        email, code = 'a', get_random_string()
        obj = cls(email, code)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.email == email
        assert stored_obj.code == code


def test_PSANonce(model, session):
    cls = model.PSANonce
    assert cls.__tablename__ == 'psa_nonce'
    with dbcleanup(session, cls):
        server_url, timestamp, salt = 'a', 1, 'b'
        obj = cls(server_url, timestamp, salt)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.server_url
        assert stored_obj.timestamp == timestamp
        assert stored_obj.salt == salt


def test_PSAPartial(model, session):
    cls = model.PSAPartial
    assert cls.__tablename__ == 'psa_partial'
    with dbcleanup(session, cls):
        token, data, next_step, backend = 'a', 'b', 1, 'c'
        obj = cls(token, data, next_step, backend)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.token == token
        assert stored_obj.data == data
        assert stored_obj.next_step == next_step
        assert stored_obj.backend == backend


def test_Quota(
        model,
        session,
        default_quota_association,
        group_quota_association,
        user_quota_association
):
    cls = model.Quota
    assert cls.__tablename__ == 'quota'
    with dbcleanup(session, cls):
        name, description, amount, operation = get_random_string(), 'b', 42, '+'
        obj = cls(name, description, amount, operation)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time

        def add_association(assoc_object, assoc_attribute):
            assoc_object.quota = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        add_association(default_quota_association, 'default')
        add_association(group_quota_association, 'groups')
        add_association(user_quota_association, 'users')

        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.bytes == amount
        assert stored_obj.operation == operation
        assert stored_obj.deleted is False
        # test mapped relationships
        assert stored_obj.default == [default_quota_association]
        assert stored_obj.groups == [group_quota_association]
        assert stored_obj.users == [user_quota_association]


def test_Role(
        model,
        session,
        dataset_permission,
        group_role_association,
        library_permission,
        library_folder_permission,
        library_dataset_permission,
        library_dataset_dataset_association_permission,
):
    cls = model.Role
    assert cls.__tablename__ == 'role'
    with dbcleanup(session, cls):
        name, description, type_, deleted = get_random_string(), 'b', cls.types.SYSTEM, True
        obj = cls(name, description, type_, deleted)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.dataset_actions.append(dataset_permission)
        obj.library_actions.append(library_permission)
        obj.library_folder_actions.append(library_folder_permission)
        obj.library_dataset_actions.append(library_dataset_permission)
        obj.library_dataset_dataset_actions.append(library_dataset_dataset_association_permission)
        obj.groups.append(group_role_association)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.type == type_
        assert stored_obj.deleted == deleted
        # test mapped relationships
        assert stored_obj.dataset_actions == [dataset_permission]
        assert stored_obj.groups == [group_role_association]
        assert stored_obj.library_actions == [library_permission]
        assert stored_obj.library_folder_actions == [library_folder_permission]
        assert stored_obj.library_dataset_actions == [library_dataset_permission]
        assert stored_obj.library_dataset_dataset_actions == [library_dataset_dataset_association_permission]


def test_StoredWorkflowAnnotationAssociation(model, session, stored_workflow, user):
    cls = model.StoredWorkflowAnnotationAssociation
    assert cls.__tablename__ == 'stored_workflow_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.stored_workflow = stored_workflow
        obj.user = user
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.stored_workflow_id == stored_workflow.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.stored_workflow.id == stored_workflow.id
        assert stored_obj.user.id == user.id


def test_StoredWorkflowRatingAssociation(model, session, stored_workflow, user):
    cls = model.StoredWorkflowRatingAssociation
    assert cls.__tablename__ == 'stored_workflow_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, stored_workflow, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.stored_workflow_id == stored_workflow.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.stored_workflow.id == stored_workflow.id
        assert stored_obj.user.id == user.id


def test_StoredWorkflowTagAssociation(model, session, stored_workflow, tag, user):
    cls = model.StoredWorkflowTagAssociation
    assert cls.__tablename__ == 'stored_workflow_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.stored_workflow_id = stored_workflow.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.stored_workflow_id == stored_workflow.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.stored_workflow.id == stored_workflow.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_Tag(
        model,
        session,
        history_tag_association,
        history_dataset_association_tag_association,
        library_dataset_dataset_association_tag_association,
        page_tag_association,
        workflow_step_tag_association,
        stored_workflow_tag_association,
        visualization_tag_association,
        history_dataset_collection_tag_association,
        library_dataset_collection_tag_association,
        tool_tag_association,
):
    cls = model.Tag
    assert cls.__tablename__ == 'tag'
    assert has_unique_constraint(cls.__table__, ('name',))

    with dbcleanup(session, cls):
        parent_tag = cls()
        child_tag = cls()
        type_, name = 1, 'a'
        obj = cls(type=type_, name=name)
        obj.parent = parent_tag
        obj.children.append(child_tag)

        def add_association(assoc_object, assoc_attribute):
            assoc_object.tag = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        add_association(history_tag_association, 'tagged_histories')
        add_association(history_dataset_association_tag_association, 'tagged_history_dataset_associations')
        add_association(library_dataset_dataset_association_tag_association, 'tagged_library_dataset_dataset_associations')
        add_association(page_tag_association, 'tagged_pages')
        add_association(workflow_step_tag_association, 'tagged_workflow_steps')
        add_association(stored_workflow_tag_association, 'tagged_stored_workflows')
        add_association(visualization_tag_association, 'tagged_visualizations')
        add_association(history_dataset_collection_tag_association, 'tagged_history_dataset_collections')
        add_association(library_dataset_collection_tag_association, 'tagged_library_dataset_collections')
        add_association(tool_tag_association, 'tagged_tools')

        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.type == type_
        assert stored_obj.parent_id == parent_tag.id
        assert stored_obj.name == name
        # test mapped relationships
        assert stored_obj.parent.id == parent_tag.id
        assert stored_obj.children == [child_tag]
        assert stored_obj.tagged_histories == [history_tag_association]
        assert stored_obj.tagged_history_dataset_associations == [history_dataset_association_tag_association]
        assert stored_obj.tagged_library_dataset_dataset_associations == [library_dataset_dataset_association_tag_association]
        assert stored_obj.tagged_pages == [page_tag_association]
        assert stored_obj.tagged_workflow_steps == [workflow_step_tag_association]
        assert stored_obj.tagged_stored_workflows == [stored_workflow_tag_association]
        assert stored_obj.tagged_visualizations == [visualization_tag_association]
        assert stored_obj.tagged_history_dataset_collections == [history_dataset_collection_tag_association]
        assert stored_obj.tagged_library_dataset_collections == [library_dataset_collection_tag_association]
        assert stored_obj.tagged_tools == [tool_tag_association]


def test_ToolTagAssociation(model, session, tag, user):
    cls = model.ToolTagAssociation
    assert cls.__tablename__ == 'tool_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value, tool_id = 'a', 'b', 'c', 'd'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.tool_id = tool_id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.tool_id == tool_id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_UserAction(model, session, user, galaxy_session):
    cls = model.UserAction
    assert cls.__tablename__ == 'user_action'
    with dbcleanup(session, cls):
        action, params, context = 'a', 'b', 'c'
        obj = cls(user, galaxy_session.id, action, params, context)
        create_time = datetime.now()
        obj.create_time = create_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.user_id == user.id
        assert stored_obj.session_id == galaxy_session.id
        assert stored_obj.action == action
        assert stored_obj.context == context
        assert stored_obj.params == params
        # test mapped relationships
        assert stored_obj.user.id == user.id


def test_UserAddress(model, session, user):
    cls = model.UserAddress
    assert cls.__tablename__ == 'user_address'
    with dbcleanup(session, cls):
        desc, name, institution, address, city, state, postal_code, country, phone, deleted, purged = \
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', True, False
        obj = cls(user, desc, name, institution, address, city, state, postal_code, country, phone)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.deleted = deleted
        obj.purged = purged
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.user_id == user.id
        assert stored_obj.desc == desc
        assert stored_obj.name == name
        assert stored_obj.institution == institution
        assert stored_obj.address == address
        assert stored_obj.city == city
        assert stored_obj.state == state
        assert stored_obj.postal_code == postal_code
        assert stored_obj.country == country
        assert stored_obj.phone == phone
        assert stored_obj.deleted == deleted
        assert stored_obj.purged == purged
        # test mapped relationships
        assert stored_obj.user.id == user.id


def test_UserAuthnzToken(model, session, user, cloud_authz):
    cls = model.UserAuthnzToken
    assert cls.__tablename__ == 'oidc_user_authnz_tokens'
    assert has_unique_constraint(cls.__table__, ('provider', 'uid'))
    with dbcleanup(session, cls):
        provider, uid, extra_data, lifetime, assoc_type = get_random_string(), 'b', 'c', 1, 'd'
        obj = cls(provider, uid, extra_data, lifetime, assoc_type, user)
        obj.cloudauthz.append(cloud_authz)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.uid == uid
        assert stored_obj.provider == provider
        assert stored_obj.extra_data == extra_data
        assert stored_obj.lifetime == lifetime
        assert stored_obj.assoc_type == assoc_type
        # test mapped relationships
        assert stored_obj.cloudauthz == [cloud_authz]
        assert stored_obj.user.id == user.id


def test_UserGroupAssociation(model, session, user, group):
    cls = model.UserGroupAssociation
    assert cls.__tablename__ == 'user_group_association'
    with dbcleanup(session, cls):
        obj = cls(user, group)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.group_id == group.id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        # test mapped relationships
        assert stored_obj.user.id == user.id
        assert stored_obj.group.id == group.id


def test_UserQuotaAssociation(model, session, user, quota):
    cls = model.UserQuotaAssociation
    assert cls.__tablename__ == 'user_quota_association'
    with dbcleanup(session, cls):
        obj = cls(user, quota)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.quota_id == quota.id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        # test mapped relationships
        assert stored_obj.user.id == user.id
        assert stored_obj.quota.id == quota.id


def test_VisualizationAnnotationAssociation(model, session, visualization, user):
    cls = model.VisualizationAnnotationAssociation
    assert cls.__tablename__ == 'visualization_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.visualization = visualization
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.visualization_id == visualization.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.visualization.id == visualization.id
        assert stored_obj.user.id == user.id


def test_VisualizationRatingAssociation(model, session, visualization, user):
    cls = model.VisualizationRatingAssociation
    assert cls.__tablename__ == 'visualization_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, visualization, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.visualization_id == visualization.id
        assert stored_obj.user_id == user.id
        assert stored_obj.rating == rating
        # test mapped relationships
        assert stored_obj.visualization.id == visualization.id
        assert stored_obj.user.id == user.id


def test_VisualizationRevision(model, session, visualization):
    cls = model.VisualizationRevision
    assert cls.__tablename__ == 'visualization_revision'
    assert has_index(cls.__table__, ('dbkey',))
    with dbcleanup(session, cls):
        visualization, title, dbkey, config = visualization, 'a', 'b', 'c'
        obj = cls(visualization, title, dbkey, config)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.create_time == create_time
        assert stored_obj.update_time == update_time
        assert stored_obj.visualization_id == visualization.id
        assert stored_obj.title == title
        assert stored_obj.dbkey == dbkey
        assert stored_obj.config == config
        # test mapped relationships
        assert stored_obj.visualization.id == visualization.id


def test_WorkerProcess(model, session):
    cls = model.WorkerProcess
    assert cls.__tablename__ == 'worker_process'
    assert has_unique_constraint(cls.__table__, ('server_name', 'hostname'))
    with dbcleanup(session, cls):
        server_name, hostname = get_random_string(), 'a'
        obj = cls(server_name, hostname)
        update_time = datetime.now()
        obj.update_time = update_time
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.server_name == server_name
        assert stored_obj.hostname == hostname
        assert stored_obj.pid is None
        assert stored_obj.update_time == update_time


def test_WorkflowStepAnnotationAssociation(model, session, workflow_step, user):
    cls = model.WorkflowStepAnnotationAssociation
    assert cls.__tablename__ == 'workflow_step_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.workflow_step = workflow_step
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.workflow_step_id == workflow_step.id
        assert stored_obj.user_id == user.id
        assert stored_obj.annotation == annotation
        # test mapped relationships
        assert stored_obj.workflow_step.id == workflow_step.id
        assert stored_obj.user.id == user.id


def test_WorkflowStepTagAssociation(model, session, workflow_step, tag, user):
    cls = model.WorkflowStepTagAssociation
    assert cls.__tablename__ == 'workflow_step_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.workflow_step_id = workflow_step.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.workflow_step_id == workflow_step.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.workflow_step.id == workflow_step.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


def test_VisualizationTagAssociation(model, session, visualization, tag, user):
    cls = model.VisualizationTagAssociation
    assert cls.__tablename__ == 'visualization_tag_association'
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.visualization_id = visualization.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        # test mapped columns
        assert stored_obj.id == obj_id
        assert stored_obj.visualization_id == visualization.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user_id == user.id
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value
        # test mapped relationships
        assert stored_obj.visualization.id == visualization.id
        assert stored_obj.tag.id == tag.id
        assert stored_obj.user.id == user.id


@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


@pytest.fixture
def cloud_authz(model, session, user, user_authnz_token):
    ca = model.CloudAuthz(user.id, 'a', 'b', user_authnz_token.id, 'c')
    yield from dbcleanup_wrapper(session, ca)


@pytest.fixture
def dataset(model, session):
    d = model.Dataset()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_collection(model, session):
    dc = model.DatasetCollection(collection_type='a')
    yield from dbcleanup_wrapper(session, dc)


@pytest.fixture
def dataset_collection_element(
        model, session, dataset_collection, history_dataset_association):
    dce = model.DatasetCollectionElement(
        collection=dataset_collection, element=history_dataset_association)
    yield from dbcleanup_wrapper(session, dce)


@pytest.fixture
def dataset_permission(model, session, dataset):
    d = model.DatasetPermissions('a', dataset)
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_source(model, session):
    d = model.DatasetSource()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_source_hash(model, session):
    d = model.DatasetSourceHash()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def default_quota_association(model, session, quota):
    type_ = model.DefaultQuotaAssociation.types.REGISTERED
    dqa = model.DefaultQuotaAssociation(type_, quota)
    yield from dbcleanup_wrapper(session, dqa)


@pytest.fixture
def form_definition(model, session, form_definition_current):
    fd = model.FormDefinition(name='a', form_definition_current=form_definition_current)
    yield from dbcleanup_wrapper(session, fd)


@pytest.fixture
def form_definition_current(model, session):
    fdc = model.FormDefinitionCurrent()
    yield from dbcleanup_wrapper(session, fdc)


@pytest.fixture
def galaxy_session(model, session, user):
    s = model.GalaxySession()
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def group(model, session):
    g = model.Group()
    yield from dbcleanup_wrapper(session, g)


@pytest.fixture
def group_quota_association(model, session):
    gqa = model.GroupQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, gqa)


@pytest.fixture
def group_role_association(model, session):
    gra = model.GroupRoleAssociation(None, None)
    yield from dbcleanup_wrapper(session, gra)


@pytest.fixture
def history(model, session):
    h = model.History()
    yield from dbcleanup_wrapper(session, h)


@pytest.fixture
def history_dataset_association(model, session, dataset):
    hda = model.HistoryDatasetAssociation(dataset=dataset)
    yield from dbcleanup_wrapper(session, hda)


@pytest.fixture
def history_dataset_association_tag_association(model, session):
    hdata = model.HistoryDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, hdata)


@pytest.fixture
def history_dataset_collection_association(model, session):
    hdca = model.HistoryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, hdca)


@pytest.fixture
def history_dataset_collection_tag_association(model, session):
    hdcta = model.HistoryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, hdcta)


@pytest.fixture
def history_tag_association(model, session):
    hta = model.HistoryTagAssociation()
    yield from dbcleanup_wrapper(session, hta)


@pytest.fixture
def job(model, session):
    j = model.Job()
    yield from dbcleanup_wrapper(session, j)


@pytest.fixture
def library(model, session):
    lb = model.Library()
    yield from dbcleanup_wrapper(session, lb)


@pytest.fixture
def library_folder(model, session):
    lf = model.LibraryFolder()
    yield from dbcleanup_wrapper(session, lf)


@pytest.fixture
def library_dataset(model, session):
    ld = model.LibraryDataset()
    yield from dbcleanup_wrapper(session, ld)


@pytest.fixture
def library_dataset_collection_association(model, session):
    ldca = model.LibraryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, ldca)


@pytest.fixture
def library_dataset_collection_tag_association(model, session):
    ldcta = model.LibraryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, ldcta)


@pytest.fixture
def library_dataset_dataset_association(model, session):
    ldda = model.LibraryDatasetDatasetAssociation()
    yield from dbcleanup_wrapper(session, ldda)


@pytest.fixture
def library_dataset_dataset_association_tag_association(model, session):
    lddata = model.LibraryDatasetDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, lddata)


@pytest.fixture
def library_dataset_permission(model, session, library_dataset, role):
    ldp = model.LibraryDatasetPermissions('a', library_dataset, role)
    yield from dbcleanup_wrapper(session, ldp)


@pytest.fixture
def library_dataset_dataset_association_permission(model, session, library_dataset_dataset_association, role):
    lddp = model.LibraryDatasetDatasetAssociationPermissions('a', library_dataset_dataset_association, role)
    yield from dbcleanup_wrapper(session, lddp)


@pytest.fixture
def library_folder_permission(model, session, library_folder, role):
    lfp = model.LibraryFolderPermissions('a', library_folder, role)
    yield from dbcleanup_wrapper(session, lfp)


@pytest.fixture
def library_permission(model, session, library, role):
    lp = model.LibraryPermissions('a', library, role)
    yield from dbcleanup_wrapper(session, lp)


@pytest.fixture
def page(model, session, user):
    p = model.Page()
    p.user = user
    yield from dbcleanup_wrapper(session, p)


@pytest.fixture
def page_revision(model, session, page):
    pr = model.PageRevision()
    pr.page = page
    yield from dbcleanup_wrapper(session, pr)


@pytest.fixture
def page_annotation_association(model, session):
    paa = model.PageAnnotationAssociation()
    yield from dbcleanup_wrapper(session, paa)


@pytest.fixture
def page_rating_association(model, session):
    pra = model.PageRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, pra)


@pytest.fixture
def page_tag_association(model, session):
    pta = model.PageTagAssociation()
    yield from dbcleanup_wrapper(session, pta)


@pytest.fixture
def page_user_share_association(model, session):
    pra = model.PageUserShareAssociation()
    yield from dbcleanup_wrapper(session, pra)


@pytest.fixture
def quota(model, session):
    q = model.Quota(get_random_string(), 'b')
    yield from dbcleanup_wrapper(session, q)


@pytest.fixture
def role(model, session):
    r = model.Role()
    yield from dbcleanup_wrapper(session, r)


@pytest.fixture
def stored_workflow(model, session, user):
    w = model.StoredWorkflow()
    w.user = user
    yield from dbcleanup_wrapper(session, w)


@pytest.fixture
def stored_workflow_tag_association(model, session):
    swta = model.StoredWorkflowTagAssociation()
    yield from dbcleanup_wrapper(session, swta)


@pytest.fixture
def tag(model, session):
    t = model.Tag()
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def tool_tag_association(model, session):
    tta = model.ToolTagAssociation()
    yield from dbcleanup_wrapper(session, tta)


@pytest.fixture
def user(model, session):
    u = model.User(email='test@example.com', password='password')
    yield from dbcleanup_wrapper(session, u)


@pytest.fixture
def user_authnz_token(model, session, user):
    t = model.UserAuthnzToken('a', 'b', 'c', 1, 'd', user)
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def user_quota_association(model, session):
    uqa = model.UserQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, uqa)


@pytest.fixture
def visualization(model, session, user):
    v = model.Visualization()
    v.user = user
    yield from dbcleanup_wrapper(session, v)


@pytest.fixture
def visualization_tag_association(model, session):
    vta = model.VisualizationTagAssociation()
    yield from dbcleanup_wrapper(session, vta)


@pytest.fixture
def workflow(model, session):
    w = model.Workflow()
    yield from dbcleanup_wrapper(session, w)


@pytest.fixture
def workflow_step(model, session, workflow):
    s = model.WorkflowStep()
    s.workflow = workflow
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def workflow_step_tag_association(model, session):
    wsta = model.WorkflowStepTagAssociation()
    yield from dbcleanup_wrapper(session, wsta)


@contextmanager
def dbcleanup(session, cls):
    """
    Ensure all records of cls are deleted from the database on exit.
    """
    try:
        yield
    finally:
        session.execute(delete(cls))


def dbcleanup_wrapper(session, obj):
    persist(session, obj)
    with dbcleanup(session, type(obj)):
        yield obj


def persist(session, obj, return_id=True):
    session.add(obj)
    session.flush()
    obj_id = obj.id if return_id else None  # save this before obj is expunged
    # Remove from session, so that on a subsequent load we get a *new* obj from the db
    session.expunge(obj)
    return obj_id


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True


def has_index(table, fields):
    for index in table.indexes:
        col_names = {c.name for c in index.columns}
        if set(fields) == col_names:
            return True


def get_stored_obj(session, cls, obj_id=None, stmt=None):
    # Either obj_id or stmt must be provided, but not both
    assert bool(obj_id) ^ (stmt is not None)
    if stmt is None:
        stmt = select(cls).where(cls.id == obj_id)
    return session.execute(stmt).scalar_one()


def get_random_string():
    """Generate unique values to accommodate unique constraints."""
    return str(random.random())
