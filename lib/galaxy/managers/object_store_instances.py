"""
To Test:
- upgrading with missing secret raise exception
- upgrading removes old secrets
- upgrading with partial variables keeps the old one
- upgrading with no variables works just fine
- upgrading and missing variables raises exception
"""

import logging
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)
from uuid import uuid4

from pydantic import UUID4

from galaxy.exceptions import (
    ItemOwnershipException,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import UserObjectStore
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import (
    BaseObjectStore,
    BaseUserObjectStoreResolver,
    build_test_object_store_from_user_config,
    ConcreteObjectStoreModel,
    QuotaModel,
    USER_OBJECTS_SCHEME,
    UserObjectStoresAppConfig,
)
from galaxy.objectstore.badges import serialize_badges
from galaxy.objectstore.templates import (
    ConfiguredObjectStoreTemplates,
    ObjectStoreConfiguration,
    ObjectStoreTemplate,
    ObjectStoreTemplateSummaries,
    ObjectStoreTemplateType,
    template_to_configuration,
)
from galaxy.security.vault import Vault
from galaxy.util.config_templates import (
    connection_exception_to_status,
    PluginAspectStatus,
    PluginStatus,
    settings_exception_to_status,
    status_template_definition,
    TemplateVariableValueType,
    validate_no_extra_secrets_defined,
    validate_no_extra_variables_defined,
)
from ._config_templates import (
    CreateInstancePayload,
    ModifyInstancePayload,
    prepare_environment,
    prepare_environment_from_root,
    purge_template_instance,
    recover_secrets,
    save_template_instance,
    sort_templates,
    update_instance_secret,
    update_template_instance,
    updated_template_variables,
    UpdateInstancePayload,
    UpdateInstanceSecretPayload,
    upgrade_secrets,
    UpgradeInstancePayload,
)

log = logging.getLogger(__name__)


class UserConcreteObjectStoreModel(ConcreteObjectStoreModel):
    uuid: UUID4
    type: ObjectStoreTemplateType
    template_id: str
    template_version: int
    variables: Optional[Dict[str, TemplateVariableValueType]]
    secrets: List[str]
    hidden: bool
    active: bool
    purged: bool


class ObjectStoreInstancesManager:
    _catalog: ConfiguredObjectStoreTemplates
    _sa_session: galaxy_scoped_session
    _app_config: UserObjectStoresAppConfig

    def __init__(
        self,
        catalog: ConfiguredObjectStoreTemplates,
        sa_session: galaxy_scoped_session,
        vault: Vault,
        app_config: UserObjectStoresAppConfig,
    ):
        self._catalog = catalog
        self._sa_session = sa_session
        self._app_vault = vault
        self._app_config = app_config

    @property
    def summaries(self) -> ObjectStoreTemplateSummaries:
        return self._catalog.summaries

    def modify_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: ModifyInstancePayload
    ) -> UserConcreteObjectStoreModel:
        if isinstance(payload, UpgradeInstancePayload):
            return self._upgrade_instance(trans, id, payload)
        elif isinstance(payload, UpdateInstanceSecretPayload):
            return self._update_instance_secret(trans, id, payload)
        else:
            assert isinstance(payload, UpdateInstancePayload)
            return self._update_instance(trans, id, payload)

    def purge_instance(self, trans: ProvidesUserContext, id: UUID4) -> None:
        persisted_object_store = self._get(trans, id)
        purge_template_instance(trans, persisted_object_store, self._app_config)

    def _upgrade_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpgradeInstancePayload
    ) -> UserConcreteObjectStoreModel:
        persisted_object_store = self._get(trans, id)
        template = self._get_template(persisted_object_store, payload.template_version)
        persisted_object_store.template_version = template.version
        persisted_object_store.template_definition = template.model_dump()
        validate_no_extra_variables_defined(payload.variables, template)
        validate_no_extra_secrets_defined(payload.secrets, template)
        actual_variables = updated_template_variables(
            payload.variables,
            persisted_object_store,
            template,
        )
        persisted_object_store.template_variables = actual_variables
        upgrade_secrets(trans, persisted_object_store, template, payload, self._app_config)
        self._save(persisted_object_store)
        return self._to_model(trans, persisted_object_store)

    def _update_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpdateInstancePayload
    ) -> UserConcreteObjectStoreModel:
        persisted_object_store = self._get(trans, id)
        template = self._get_template(persisted_object_store)
        update_template_instance(self._sa_session, persisted_object_store, payload, template)
        return self._to_model(trans, persisted_object_store)

    def _update_instance_secret(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpdateInstanceSecretPayload
    ) -> UserConcreteObjectStoreModel:
        persisted_object_store = self._get(trans, id)
        template = self._get_template(persisted_object_store)
        update_instance_secret(trans, persisted_object_store, template, payload, self._app_config)
        return self._to_model(trans, persisted_object_store)

    def create_instance(
        self, trans: ProvidesUserContext, payload: CreateInstancePayload
    ) -> UserConcreteObjectStoreModel:
        catalog = self._catalog
        catalog.validate(payload)
        template = catalog.find_template(payload)
        assert template
        user_vault = trans.user_vault
        persisted_object_store = UserObjectStore()
        persisted_object_store.user_id = trans.user.id
        assert persisted_object_store.user_id
        persisted_object_store.uuid = uuid4().hex
        persisted_object_store.template_definition = template.model_dump()
        persisted_object_store.template_id = template.id
        persisted_object_store.template_version = template.version
        persisted_object_store.template_variables = payload.variables
        persisted_object_store.name = payload.name
        persisted_object_store.description = payload.description
        self._save(persisted_object_store)

        # the exception handling below will cleanup object stores that cannot be
        # finalized with a successful secret setting but it might be worth considering
        # something more robust. Two ideas would be to set a uuid on the persisted_object_store
        # and key the secrets on that instead of the of the ID (but this raises the question
        # are unused secrets in the vault maybe even worse than broken db objects) or
        # set a state on the DB objects and with INITIAL and ACTIVE states. State
        # idea might be nice because then we could add INACTIVE state that would prevent
        # new data from being added but still allow access.
        recorded_secrets = []
        try:
            for secret, value in payload.secrets.items():
                key = persisted_object_store.vault_key(secret, self._app_config)
                user_vault.write_secret(key, value)
                recorded_secrets.append(secret)
        except Exception:
            self._sa_session.delete(persisted_object_store)
            raise
        persisted_object_store.template_secrets = recorded_secrets
        self._save(persisted_object_store)
        return self._to_model(trans, persisted_object_store)

    def index(self, trans: ProvidesUserContext) -> List[UserConcreteObjectStoreModel]:
        stores = self._sa_session.query(UserObjectStore).filter(UserObjectStore.user_id == trans.user.id).all()
        return [self._to_model(trans, s) for s in stores]

    def show(self, trans: ProvidesUserContext, id: UUID4) -> UserConcreteObjectStoreModel:
        user_object_store = self._get(trans, id)
        return self._to_model(trans, user_object_store)

    def _save(self, persisted_object_store: UserObjectStore) -> None:
        save_template_instance(self._sa_session, persisted_object_store)

    def _get(self, trans: ProvidesUserContext, id: UUID4) -> UserObjectStore:
        filter = self._index_filter(id)
        user_object_store = self._sa_session.query(UserObjectStore).filter(filter).one_or_none()
        if user_object_store is None:
            raise RequestParameterInvalidException(f"Failed to fetch object store for id {id}")
        if user_object_store.user != trans.user:
            raise ItemOwnershipException()
        return user_object_store

    def plugin_status(self, trans: ProvidesUserContext, payload: CreateInstancePayload) -> PluginStatus:
        template = self._catalog.find_template(payload)
        template_definition_status = status_template_definition(template)
        status_kwds = {"template_definition": template_definition_status}
        if template_definition_status.is_not_ok:
            return PluginStatus(**status_kwds)
        assert template
        configuration, template_settings_status = self._template_settings_status(trans, payload, template)
        status_kwds["template_settings"] = template_settings_status
        if template_settings_status.is_not_ok:
            return PluginStatus(**status_kwds)
        assert configuration
        object_store, connection_status = self._connection_status(trans, payload, configuration)
        status_kwds["connection"] = connection_status
        if connection_status.is_not_ok:
            return PluginStatus(**status_kwds)
        assert object_store
        # Lets circle back to this - we need to add an entry point to the file source plugins
        # to test if things are writable. We could ping remote APIs or do something like os.access('/path/to/folder', os.W_OK)
        # locally.
        return PluginStatus(**status_kwds)

    def _template_settings_status(
        self,
        trans: ProvidesUserContext,
        payload: CreateInstancePayload,
        template: ObjectStoreTemplate,
    ) -> Tuple[Optional[ObjectStoreConfiguration], PluginAspectStatus]:
        secrets = payload.secrets
        variables = payload.variables
        environment = prepare_environment_from_root(template.environment, self._app_vault, self._app_config)
        user_details = trans.user.config_template_details()

        configuration = None
        exception = None
        try:
            configuration = template_to_configuration(
                template,
                variables=variables,
                secrets=secrets,
                user_details=user_details,
                environment=environment,
            )
        except Exception as e:
            exception = e
        return configuration, settings_exception_to_status(exception)

    def _connection_status(
        self, trans: ProvidesUserContext, payload: CreateInstancePayload, configuration: ObjectStoreConfiguration
    ) -> Tuple[Optional[BaseObjectStore], PluginAspectStatus]:
        object_store = None
        exception = None
        try:
            object_store = build_test_object_store_from_user_config(trans.app.config, configuration)
        except Exception as e:
            exception = e
        return object_store, connection_exception_to_status("storage location", exception)

    def _index_filter(self, uuid: UUID4):
        return UserObjectStore.__table__.c.uuid == uuid

    def _get_template(
        self, persisted_object_store: UserObjectStore, template_version: Optional[int] = None
    ) -> ObjectStoreTemplate:
        catalog = self._catalog
        target_template_version = template_version or persisted_object_store.template_version
        template = catalog.find_template_by(persisted_object_store.template_id, target_template_version)
        return template

    def _to_model(self, trans, persisted_object_store: UserObjectStore) -> UserConcreteObjectStoreModel:
        quota = QuotaModel(source=None, enabled=False)
        object_store_type = persisted_object_store.template.configuration.type
        admin_badges = persisted_object_store.template.configuration.badges or []
        badges = serialize_badges(
            admin_badges,
            False,
            True,
            True,
            object_store_type in ["azure_blob", "s3"],
        )
        secrets = persisted_object_store.template_secrets or []
        uuid = str(persisted_object_store.uuid)
        object_store_id = f"{USER_OBJECTS_SCHEME}{uuid}"

        return UserConcreteObjectStoreModel(
            uuid=uuid,
            type=object_store_type,
            template_id=persisted_object_store.template_id,
            template_version=persisted_object_store.template_version,
            variables=persisted_object_store.template_variables,
            secrets=secrets,
            name=persisted_object_store.name,
            description=persisted_object_store.description,
            object_store_id=object_store_id,
            private=True,
            quota=quota,
            badges=badges,
            hidden=persisted_object_store.hidden,
            active=persisted_object_store.active,
            purged=persisted_object_store.purged,
        )


class UserObjectStoreResolverImpl(BaseUserObjectStoreResolver):
    def __init__(
        self,
        sa_session: galaxy_scoped_session,
        vault: Vault,
        app_config: UserObjectStoresAppConfig,
        catalog: ConfiguredObjectStoreTemplates,
    ):
        self._sa_session = sa_session
        self._vault = vault
        self._app_config = app_config
        self._catalog = catalog

    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        user_object_store_id = uri.split("://", 1)[1]
        index_filter = UserObjectStore.__table__.c.uuid == user_object_store_id
        user_object_store: UserObjectStore = self._sa_session.query(UserObjectStore).filter(index_filter).one()
        secrets = recover_secrets(user_object_store, self._vault, self._app_config)
        environment = prepare_environment(user_object_store, self._vault, self._app_config)
        templates = sort_templates(
            self._app_config,
            self._catalog.catalog.root,
            user_object_store,
        )
        object_store_configuration = user_object_store.object_store_configuration(
            secrets=secrets, environment=environment, templates=templates
        )
        return object_store_configuration


__all__ = (
    "CreateInstancePayload",
    "ModifyInstancePayload",
    "UpdateInstancePayload",
    "UpdateInstanceSecretPayload",
    "UpgradeInstancePayload",
    "UserObjectStoreResolverImpl",
    "UserConcreteObjectStoreModel",
    "ObjectStoreInstancesManager",
)
