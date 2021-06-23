import random
from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import (
    delete,
    select,
    UniqueConstraint,
)

import galaxy.model.mapping as mapping


def testAPIKeys(model, session, user):
    cls = model.APIKeys
    assert cls.__tablename__ == 'api_keys'
    with dbcleanup(session, cls):
        user_id, key = user.id, 'a'
        obj = cls(user_id, key)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user_id
        assert stored_obj.key == key
        assert stored_obj.user.id == user.id


def test_CloudAuthz(model, session, user, user_authnz_token):
    cls = model.CloudAuthz
    assert cls.__tablename__ == 'cloudauthz'
    with dbcleanup(session, cls):
        provider, config, description = 'a', 'b', 'c'
        obj = cls(user.id, provider, config, user_authnz_token.id, description)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.provider == provider
        assert stored_obj.config == config
        assert stored_obj.authn_id == user_authnz_token.id
        assert stored_obj.description == description
        assert stored_obj.tokens is None
        assert stored_obj.last_update
        assert stored_obj.last_activity
        assert stored_obj.create_time
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
        assert stored_obj.id == obj_id
        assert stored_obj.external_user_id == external_user_id
        assert stored_obj.provider == provider
        assert stored_obj.access_token == access_token
        assert stored_obj.id_token == id_token
        assert stored_obj.refresh_token == refresh_token
        assert stored_obj.expiration_time == expiration_time
        assert stored_obj.refresh_expiration_time == refresh_expiration_time
        assert stored_obj.user == user


def test_DatasetPermissions(model, session, dataset, role):
    cls = model.DatasetPermissions
    assert cls.__tablename__ == 'dataset_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(action, dataset, role)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.action == action
        assert stored_obj.dataset == dataset
        assert stored_obj.role == role


def test_DefaultQuotaAssociation(model, session, quota):
    cls = model.DefaultQuotaAssociation
    assert cls.__tablename__ == 'default_quota_association'
    with dbcleanup(session, cls):
        type = cls.types.REGISTERED
        obj = cls(type, quota)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.type == type
        assert stored_obj.quota == quota


def test_DefaultUserPermissions(model, session, user, role):
    cls = model.DefaultUserPermissions
    assert cls.__tablename__ == 'default_user_permissions'
    with dbcleanup(session, cls):
        action = 'a'
        obj = cls(user, action, role)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.action == action
        assert stored_obj.role == role


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
        obj.workflow_steps.append(workflow_step)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.tool_format == tool_format
        assert stored_obj.tool_id == tool_id
        assert stored_obj.tool_version == tool_version
        assert stored_obj.tool_path == tool_path
        assert stored_obj.tool_directory == tool_directory
        assert stored_obj.uuid
        assert stored_obj.active == active
        assert stored_obj.hidden == hidden
        assert stored_obj.value == value
        assert workflow_step in stored_obj.workflow_steps


def test_GroupQuotaAssociation(model, session, group, quota):
    cls = model.GroupQuotaAssociation
    assert cls.__tablename__ == 'group_quota_association'
    with dbcleanup(session, cls):
        obj = cls(group, quota)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.group == group
        assert stored_obj.quota == quota


def test_GroupRoleAssociation(model, session, group, role):
    cls = model.GroupRoleAssociation
    assert cls.__tablename__ == 'group_role_association'
    with dbcleanup(session, cls):
        obj = cls(group, role)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.group == group
        assert stored_obj.role == role


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
        assert stored_obj.id == obj_id
        assert stored_obj.history == history
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


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
        assert stored_obj.id == obj_id
        assert stored_obj.hda == history_dataset_association
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_HistoryDatasetAssociationRatingAssociation(model, session, history_dataset_association, user):
    cls = model.HistoryDatasetAssociationRatingAssociation
    assert cls.__tablename__ == 'history_dataset_association_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history_dataset_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.history_dataset_association == history_dataset_association
        assert stored_obj.rating == rating


def test_HistoryDatasetAssociationTagAssociation(
        model, session, history_dataset_association, tag, user):
    cls = model.HistoryDatasetAssociationTagAssociation
    # TODO assert cls.__tablename__ == ''
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history_dataset_association_id = history_dataset_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_association_id == history_dataset_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user == user
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value


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
        assert stored_obj.id == obj_id
        assert stored_obj.history_dataset_collection == history_dataset_collection_association
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_HistoryDatasetCollectionRatingAssociation(
        model, session, history_dataset_collection_association, user):
    cls = model.HistoryDatasetCollectionRatingAssociation
    assert cls.__tablename__ == 'history_dataset_collection_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history_dataset_collection_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.dataset_collection == history_dataset_collection_association
        assert stored_obj.rating == rating


def test_HistoryRatingAssociation(model, session, history, user):
    cls = model.HistoryRatingAssociation
    assert cls.__tablename__ == 'history_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, history, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.history == history
        assert stored_obj.rating == rating


def test_HistoryTagAssociation(model, session, history, tag, user):
    cls = model.HistoryTagAssociation
    # TODO assert cls.__tablename__ == ''
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history_id = history.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.history_id == history.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user == user
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value


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
        assert stored_obj.id == obj_id
        assert stored_obj.dataset_collection == library_dataset_collection_association
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_LibraryDatasetCollectionRatingAssociation(
        model, session, library_dataset_collection_association, user):
    cls = model.LibraryDatasetCollectionRatingAssociation
    assert cls.__tablename__ == 'library_dataset_collection_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, library_dataset_collection_association, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.dataset_collection == library_dataset_collection_association
        assert stored_obj.rating == rating


def test_LibraryDatasetDatasetAssociationTagAssociation(
        model, session, library_dataset_dataset_association, tag, user):
    cls = model.LibraryDatasetDatasetAssociationTagAssociation
    # TODO assert cls.__tablename__ == ''
    with dbcleanup(session, cls):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls(user=user, tag_id=tag.id, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.library_dataset_dataset_association_id = library_dataset_dataset_association.id
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
        assert stored_obj.tag_id == tag.id
        assert stored_obj.user == user
        assert stored_obj.user_tname == user_tname
        assert stored_obj.value == value
        assert stored_obj.user_value == user_value


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
        assert stored_obj.id == obj_id
        assert stored_obj.page == page
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_PageRatingAssociation(model, session, page, user):
    cls = model.PageRatingAssociation
    assert cls.__tablename__ == 'page_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, page, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.page == page
        assert stored_obj.rating == rating


def test_PageRevision(model, session, page):
    cls = model.PageRevision
    assert cls.__tablename__ == 'page_revision'
    with dbcleanup(session, cls):
        obj = cls()
        obj.page = page
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.page_id == page.id
        assert stored_obj.title is None
        assert stored_obj.content is None
        assert stored_obj.content_format == model.PageRevision.DEFAULT_CONTENT_FORMAT
        assert stored_obj.page.id == page.id


def test_PageUserShareAssociation(model, session, page, user):
    cls = model.PageUserShareAssociation
    assert cls.__tablename__ == 'page_user_share_association'
    with dbcleanup(session, cls):
        obj = cls()
        obj.page = page
        obj.user = user
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.page == page
        assert stored_obj.user == user


def test_PSAAssociation(model, session):
    cls = model.PSAAssociation
    assert cls.__tablename__ == 'psa_association'
    with dbcleanup(session, cls):
        server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
        obj = cls(server_url, handle, secret, issued, lifetime, assoc_type)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
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
        assert stored_obj.id == obj_id
        assert stored_obj.token == token
        assert stored_obj.data == data
        assert stored_obj.next_step == next_step
        assert stored_obj.backend == backend


def test_Quota(model, session):
    cls = model.Quota
    assert cls.__tablename__ == 'quota'
    with dbcleanup(session, cls):
        name, description = get_random_string(), 'b'
        obj = cls(name, description)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.bytes == 0
        assert stored_obj.operation == '='
        assert stored_obj.deleted is False


def test_Role(model, session):
    cls = model.Role
    assert cls.__tablename__ == 'role'
    with dbcleanup(session, cls):
        name, description = get_random_string(), 'b'
        obj = cls(name, description)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.name == name
        assert stored_obj.description == description
        assert stored_obj.type == model.Role.types.SYSTEM
        assert stored_obj.deleted is False


def test_StoredWorkflowAnnotationAssociation(model, session, stored_workflow, user):
    cls = model.StoredWorkflowAnnotationAssociation
    assert cls.__tablename__ == 'stored_workflow_annotation_association'
    assert has_index(cls.__table__, ('annotation',))
    with dbcleanup(session, cls):
        annotation = 'a'
        obj = cls()
        obj.user = user
        obj.stored_workflow = stored_workflow
        obj.annotation = annotation
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.stored_workflow == stored_workflow
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_StoredWorkflowRatingAssociation(model, session, stored_workflow, user):
    cls = model.StoredWorkflowRatingAssociation
    assert cls.__tablename__ == 'stored_workflow_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, stored_workflow, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.stored_workflow == stored_workflow
        assert stored_obj.rating == rating


def testUserAction(model, session, user, galaxy_session):
    cls = model.UserAction
    assert cls.__tablename__ == 'user_action'
    with dbcleanup(session, cls):
        action, params, context = 'a', 'b', 'c'
        obj = cls(user, galaxy_session.id, action, params, context)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.user_id == user.id
        assert stored_obj.session_id == galaxy_session.id
        assert stored_obj.action == action
        assert stored_obj.context == context
        assert stored_obj.params == params
        assert stored_obj.user.id == user.id


def test_UserAddress(model, session, user):
    cls = model.UserAddress
    assert cls.__tablename__ == 'user_address'
    with dbcleanup(session, cls):
        desc, name, institution, address, city, state, postal_code, country, phone = \
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i'
        obj = cls(user, desc, name, institution, address, city, state, postal_code, country, phone)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
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
        assert stored_obj.deleted is False
        assert stored_obj.purged is False
        assert stored_obj.user == user


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
        assert stored_obj.id == obj_id
        assert stored_obj.user_id == user.id
        assert stored_obj.uid == uid
        assert stored_obj.provider == provider
        assert stored_obj.extra_data == extra_data
        assert stored_obj.lifetime == lifetime
        assert stored_obj.assoc_type == assoc_type
        assert stored_obj.user.id == user.id
        assert cloud_authz in stored_obj.cloudauthz


def test_UserGroupAssociation(model, session, user, group):
    cls = model.UserGroupAssociation
    assert cls.__tablename__ == 'user_group_association'
    with dbcleanup(session, cls):
        obj = cls(user, group)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.group == group


def test_UserQuotaAssociation(model, session, user, quota):
    cls = model.UserQuotaAssociation
    assert cls.__tablename__ == 'user_quota_association'
    with dbcleanup(session, cls):
        obj = cls(user, quota)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.quota == quota


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
        assert stored_obj.id == obj_id
        assert stored_obj.visualization == visualization
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


def test_VisualizationRatingAssociation(model, session, visualization, user):
    cls = model.VisualizationRatingAssociation
    assert cls.__tablename__ == 'visualization_rating_association'
    with dbcleanup(session, cls):
        rating = 9
        obj = cls(user, visualization, rating)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.user == user
        assert stored_obj.visualization == visualization
        assert stored_obj.rating == rating


def test_VisualizationRevision(model, session, visualization):
    cls = model.VisualizationRevision
    assert cls.__tablename__ == 'visualization_revision'
    assert has_index(cls.__table__, ('dbkey',))
    with dbcleanup(session, cls):
        visualization, title, dbkey, config = visualization, 'a', 'b', 'c'
        obj = cls(visualization, title, dbkey, config)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.create_time
        assert stored_obj.update_time
        assert stored_obj.visualization_id == visualization.id
        assert stored_obj.title == title
        assert stored_obj.dbkey == dbkey
        assert stored_obj.config == config
        assert stored_obj.visualization.id == visualization.id


def test_WorkerProcess(model, session):
    cls = model.WorkerProcess
    assert cls.__tablename__ == 'worker_process'
    assert has_unique_constraint(cls.__table__, ('server_name', 'hostname'))
    with dbcleanup(session, cls):
        server_name, hostname = get_random_string(), 'a'
        obj = cls(server_name, hostname)
        obj_id = persist(session, obj)

        stored_obj = get_stored_obj(session, cls, obj_id)
        assert stored_obj.id == obj_id
        assert stored_obj.server_name == server_name
        assert stored_obj.hostname == hostname
        assert stored_obj.pid is None
        assert stored_obj.update_time


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
        assert stored_obj.id == obj_id
        assert stored_obj.workflow_step == workflow_step
        assert stored_obj.user == user
        assert stored_obj.annotation == annotation


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
def history(model, session):
    h = model.History()
    yield from dbcleanup_wrapper(session, h)


@pytest.fixture
def history_dataset_association(model, session, dataset):
    hda = model.HistoryDatasetAssociation(dataset=dataset)
    yield from dbcleanup_wrapper(session, hda)


@pytest.fixture
def history_dataset_collection_association(model, session):
    hdca = model.HistoryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, hdca)


@pytest.fixture
def galaxy_session(model, session, user):
    s = model.GalaxySession()
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def group(model, session):
    g = model.Group()
    yield from dbcleanup_wrapper(session, g)


@pytest.fixture
def library_dataset_collection_association(model, session):
    ldca = model.LibraryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, ldca)


@pytest.fixture
def library_dataset_dataset_association(model, session):
    ldda = model.LibraryDatasetDatasetAssociation()
    yield from dbcleanup_wrapper(session, ldda)


@pytest.fixture
def page(model, session, user):
    p = model.Page()
    p.user = user
    yield from dbcleanup_wrapper(session, p)


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
def tag(model, session):
    t = model.Tag()
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def user(model, session):
    u = model.User(email='test@example.com', password='password')
    yield from dbcleanup_wrapper(session, u)


@pytest.fixture
def user_authnz_token(model, session, user):
    t = model.UserAuthnzToken('a', 'b', 'c', 1, 'd', user)
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def visualization(model, session, user):
    v = model.Visualization()
    v.user = user
    yield from dbcleanup_wrapper(session, v)


@pytest.fixture
def workflow(model, session):
    w = model.Workflow()
    yield from dbcleanup_wrapper(session, w)


@pytest.fixture
def workflow_step(model, session, workflow):
    s = model.WorkflowStep()
    s.workflow = workflow
    yield from dbcleanup_wrapper(session, s)


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


def persist(session, obj):
    session.add(obj)
    session.flush()
    obj_id = obj.id
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


def get_stored_obj(session, cls, obj_id):
    stmt = select(cls).filter(cls.id == obj_id)
    return session.execute(stmt).scalar_one()


def get_random_string():
    """Generate unique values to accommodate unique constraints."""
    return str(random.random())
