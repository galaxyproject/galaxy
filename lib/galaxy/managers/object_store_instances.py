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
    Union,
)

from pydantic import BaseModel

from galaxy.exceptions import (
    ItemOwnershipException,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    OBJECT_STORE_TEMPLATE_CONFIGURATION_VARIABLES_TYPE,
    User,
    UserObjectStore,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import (
    BaseUserObjectStoreResolver,
    ConcreteObjectStoreModel,
    QuotaModel,
    UserObjectStoresAppConfig,
)
from galaxy.objectstore.badges import serialize_badges
from galaxy.objectstore.templates import (
    ConfiguredObjectStoreTemplates,
    ObjectStoreConfiguration,
    ObjectStoreTemplateSummaries,
    ObjectStoreTemplateType,
)
from galaxy.objectstore.templates.models import ObjectStoreTemplateVariableValueType
from galaxy.security.vault import (
    UserVaultWrapper,
    Vault,
)

log = logging.getLogger(__name__)


class CreateInstancePayload(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: str
    template_version: int
    variables: Dict[str, ObjectStoreTemplateVariableValueType]
    secrets: Dict[str, str]


class UpdateInstancePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[Dict[str, ObjectStoreTemplateVariableValueType]] = None


class UpdateInstanceSecretPayload(BaseModel):
    secret_name: str
    secret_value: str


class UpgradeInstancePayload(BaseModel):
    template_version: int
    variables: Dict[str, ObjectStoreTemplateVariableValueType]
    secrets: Dict[str, str]


class UserConcreteObjectStoreModel(ConcreteObjectStoreModel):
    id: int
    type: ObjectStoreTemplateType
    template_id: str
    template_version: int
    variables: Optional[Dict[str, ObjectStoreTemplateVariableValueType]]
    secrets: List[str]


ModifyInstancePayload = Union[UpdateInstanceSecretPayload, UpgradeInstancePayload, UpdateInstancePayload]


class ObjectStoreInstancesManager:
    _catalog: ConfiguredObjectStoreTemplates
    _sa_session: galaxy_scoped_session

    def __init__(
        self,
        catalog: ConfiguredObjectStoreTemplates,
        sa_session: galaxy_scoped_session,
        vault: Vault,
    ):
        self._catalog = catalog
        self._sa_session = sa_session
        self._app_vault = vault

    @property
    def summaries(self) -> ObjectStoreTemplateSummaries:
        return self._catalog.summaries

    def modify_instance(
        self, trans: ProvidesUserContext, id: Union[str, int], payload: ModifyInstancePayload
    ) -> UserConcreteObjectStoreModel:
        if isinstance(payload, UpgradeInstancePayload):
            return self._upgrade_instance(trans, id, payload)
        elif isinstance(payload, UpdateInstanceSecretPayload):
            return self._update_instance_secret(trans, id, payload)
        else:
            assert isinstance(payload, UpdateInstancePayload)
            return self._update_instance(trans, id, payload)

    def _upgrade_instance(
        self, trans: ProvidesUserContext, id: Union[str, int], payload: UpgradeInstancePayload
    ) -> UserConcreteObjectStoreModel:
        persisted_object_store = self._get(trans, id)
        catalog = self._catalog
        template = catalog.find_template_by(persisted_object_store.object_store_template_id, payload.template_version)
        persisted_object_store.object_store_template_version = template.version
        persisted_object_store.object_store_template_definition = template.model_dump()
        old_variables = persisted_object_store.object_store_template_variables or {}
        updated_variables = payload.variables
        actual_variables: OBJECT_STORE_TEMPLATE_CONFIGURATION_VARIABLES_TYPE = {}
        for variable in template.variables or []:
            variable_name = variable.name
            old_value = old_variables.get(variable_name)
            updated_value = updated_variables.get(variable_name, old_value)
            if updated_value:
                actual_variables[variable_name] = updated_value

        persisted_object_store.object_store_template_variables = actual_variables
        old_secrets = persisted_object_store.object_store_template_secrets or []
        new_secrets = payload.secrets

        recorded_secrets = persisted_object_store.object_store_template_secrets or []

        user_vault = trans.user_vault
        upgraded_template_secrets = []
        for secret in template.secrets or []:
            secret_name = secret.name
            upgraded_template_secrets.append(secret_name)
            if secret_name not in new_secrets and secret_name not in old_secrets:
                raise RequestParameterMissingException(f"secret {secret_name} not set in supplied request")
            if secret_name not in new_secrets:
                # keep old value
                continue

            secret_value = new_secrets[secret_name]
            key = user_vault_key(persisted_object_store, secret_name)
            user_vault.write_secret(key, secret_value)
            if secret_name not in recorded_secrets:
                recorded_secrets.append(secret_name)

        secrets_to_delete: List[str] = []
        for recorded_secret in recorded_secrets:
            if recorded_secret not in upgraded_template_secrets:
                key = user_vault_key(persisted_object_store, recorded_secret)
                log.info(f"deleting {key} from user vault")
                user_vault.delete_secret(key)
                secrets_to_delete.append(recorded_secret)

        for secret_to_delete in secrets_to_delete:
            recorded_secrets.remove(secret_to_delete)

        persisted_object_store.object_store_template_secrets = recorded_secrets
        self._save(persisted_object_store)
        rval = self._to_model(trans, persisted_object_store)
        return rval

    def _update_instance(
        self, trans: ProvidesUserContext, id: Union[str, int], payload: UpdateInstancePayload
    ) -> UserConcreteObjectStoreModel:
        # TODO: validate variables
        # TODO: test case for access control
        # TODO: test case for nulling update fields...
        persisted_object_store = self._get(trans, id)
        if payload.name is not None:
            persisted_object_store.name = payload.name
        if payload.description is not None:
            persisted_object_store.description = payload.description
        if payload.variables is not None:
            # maybe just record the valid variables according to template like in upgrade
            persisted_object_store.object_store_template_variables = payload.variables
        self._save(persisted_object_store)
        return self._to_model(trans, persisted_object_store)

    def _update_instance_secret(
        self, trans: ProvidesUserContext, id: Union[str, int], payload: UpdateInstanceSecretPayload
    ) -> UserConcreteObjectStoreModel:
        persisted_object_store = self._get(trans, id)
        user_vault = trans.user_vault
        key = user_vault_key(persisted_object_store, payload.secret_name)
        user_vault.write_secret(key, payload.secret_value)
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
        persisted_object_store.object_store_template_definition = template.model_dump()
        persisted_object_store.object_store_template_id = template.id
        persisted_object_store.object_store_template_version = template.version
        persisted_object_store.object_store_template_variables = payload.variables
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
                key = user_vault_key(persisted_object_store, secret)
                user_vault.write_secret(key, value)
                recorded_secrets.append(secret)
        except Exception:
            self._sa_session.delete(persisted_object_store)
            raise
        persisted_object_store.object_store_template_secrets = recorded_secrets
        self._save(persisted_object_store)
        return self._to_model(trans, persisted_object_store)

    def index(self, trans: ProvidesUserContext) -> List[UserConcreteObjectStoreModel]:
        stores = self._sa_session.query(UserObjectStore).filter(UserObjectStore.user_id == trans.user.id).all()
        return [self._to_model(trans, s) for s in stores]

    def show(self, trans: ProvidesUserContext, id: Union[str, int]) -> UserConcreteObjectStoreModel:
        user_object_store = self._get(trans, id)
        return self._to_model(trans, user_object_store)

    def _save(self, persisted_object_store: UserObjectStore) -> None:
        self._sa_session.add(persisted_object_store)
        self._sa_session.flush([persisted_object_store])
        self._sa_session.commit()

    def _get(self, trans: ProvidesUserContext, id: Union[str, int]) -> UserObjectStore:
        user_object_store = self._sa_session.query(UserObjectStore).get(int(id))
        if user_object_store is None:
            raise RequestParameterInvalidException(f"Failed to fetch object store for id {id}")
        if user_object_store.user != trans.user:
            raise ItemOwnershipException()
        return user_object_store

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
        # These shouldn't be null but sometimes can be?
        secrets = persisted_object_store.object_store_template_secrets or []
        return UserConcreteObjectStoreModel(
            id=persisted_object_store.id,
            type=object_store_type,
            template_id=persisted_object_store.object_store_template_id,
            template_version=persisted_object_store.object_store_template_version,
            variables=persisted_object_store.object_store_template_variables,
            secrets=secrets,
            name=persisted_object_store.name,
            description=persisted_object_store.description,
            object_store_id=f"user_objects://{persisted_object_store.id}",
            private=True,
            quota=quota,
            badges=badges,
        )


def user_vault_key(user_object_store: UserObjectStore, secret: str) -> str:
    uos_id = user_object_store.id
    assert uos_id
    user_vault_id_prefix = f"object_store_config/{uos_id}"
    key = f"{user_vault_id_prefix}/{secret}"
    return key


def recover_secrets(user_object_store: UserObjectStore, vault: Vault) -> Dict[str, str]:
    user: User = user_object_store.user
    user_vault = UserVaultWrapper(vault, user)
    secrets: Dict[str, str] = {}
    # now we could recover the list of secrets to fetch from...
    # ones recorded as written in the persisted object, the ones
    # expected in the catalog, or the ones expected in the definition
    # persisted.
    persisted_secret_names = user_object_store.object_store_template_secrets or []
    for secret in persisted_secret_names:
        vault_key = user_vault_key(user_object_store, secret)
        secret_value = user_vault.read_secret(vault_key)
        # assert secret_value
        if secret_value is not None:
            secrets[secret] = secret_value
    return secrets


class UserObjectStoreResolverImpl(BaseUserObjectStoreResolver):
    def __init__(self, sa_session: galaxy_scoped_session, vault: Vault, app_config: UserObjectStoresAppConfig):
        self._sa_session = sa_session
        self._vault = vault
        self._app_config = app_config

    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        user_object_store_id = uri.split("://", 1)[1]
        id_filter = UserObjectStore.__table__.c.id == user_object_store_id
        user_object_store: UserObjectStore = self._sa_session.query(UserObjectStore).filter(id_filter).one()
        secrets = recover_secrets(user_object_store, self._vault)
        object_store_configuration = user_object_store.object_store_configuration(secrets=secrets)
        return object_store_configuration
