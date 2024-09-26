import logging
from typing import (
    Any,
    cast,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import uuid4

from pydantic import (
    BaseModel,
    UUID4,
    ValidationError,
)

from galaxy.exceptions import (
    ItemOwnershipException,
    RequestParameterInvalidException,
)
from galaxy.files import (
    FileSourceScore,
    FileSourcesUserContext,
    ProvidesFileSourcesUserContext,
    UserDefinedFileSources,
)
from galaxy.files.plugins import (
    FileSourcePluginLoader,
    FileSourcePluginsConfig,
)
from galaxy.files.sources import (
    BaseFilesSource,
    file_source_type_is_browsable,
    FilesSourceProperties,
    PluginKind,
    SupportsBrowsing,
)
from galaxy.files.templates import (
    ConfiguredFileSourceTemplates,
    FileSourceConfiguration,
    FileSourceTemplate,
    FileSourceTemplateSummaries,
    FileSourceTemplateType,
    template_to_configuration,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    User,
    UserFileSource,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.security.vault import Vault
from galaxy.util.config_templates import (
    connection_exception_to_status,
    PluginAspectStatus,
    PluginStatus,
    settings_exception_to_status,
    status_template_definition,
    TemplateReference,
    TemplateVariableValueType,
    validate_no_extra_secrets_defined,
    validate_no_extra_variables_defined,
)
from galaxy.util.plugin_config import plugin_source_from_dict
from ._config_templates import (
    CanTestPluginStatus,
    CreateInstancePayload,
    ModifyInstancePayload,
    prepare_environment,
    prepare_template_parameters_for_testing,
    purge_template_instance,
    recover_secrets,
    save_template_instance,
    sort_templates,
    TestModifyInstancePayload,
    TestUpdateInstancePayload,
    TestUpgradeInstancePayload,
    to_template_reference,
    update_instance_secret,
    update_template_instance,
    updated_template_variables,
    UpdateInstancePayload,
    UpdateInstanceSecretPayload,
    UpdateTestTarget,
    upgrade_secrets,
    UpgradeInstancePayload,
    UpgradeTestTarget,
)

log = logging.getLogger(__name__)

USER_FILE_SOURCES_SCHEME = "gxuserfiles"


class UserFileSourceModel(BaseModel):
    uuid: UUID4
    uri_root: str
    name: str
    description: Optional[str]
    hidden: bool
    active: bool
    purged: bool
    type: FileSourceTemplateType
    template_id: str
    template_version: int
    variables: Optional[Dict[str, TemplateVariableValueType]]
    secrets: List[str]


class UserDefinedFileSourcesConfig(BaseModel):
    user_config_templates_use_saved_configuration: Literal["fallback", "preferred", "never"]

    @staticmethod
    def from_app_config(config) -> "UserDefinedFileSourcesConfig":
        user_config_templates_use_saved_configuration = config.user_config_templates_use_saved_configuration
        assert user_config_templates_use_saved_configuration in ["fallback", "preferred", "never"]
        return UserDefinedFileSourcesConfig(
            user_config_templates_use_saved_configuration=user_config_templates_use_saved_configuration,
        )


class FileSourceInstancesManager:
    _catalog: ConfiguredFileSourceTemplates
    _sa_session: galaxy_scoped_session
    _app_vault: Vault
    _app_config: UserDefinedFileSourcesConfig
    _resolver: "UserDefinedFileSourcesImpl"

    def __init__(
        self,
        catalog: ConfiguredFileSourceTemplates,
        sa_session: galaxy_scoped_session,
        vault: Vault,
        app_config: UserDefinedFileSourcesConfig,
        resolver: "UserDefinedFileSourcesImpl",
    ):
        self._catalog = catalog
        self._sa_session = sa_session
        self._app_vault = vault
        self._app_config = app_config
        self._resolver = resolver

    @property
    def summaries(self) -> FileSourceTemplateSummaries:
        return self._catalog.summaries

    def index(self, trans: ProvidesUserContext) -> List[UserFileSourceModel]:
        stores = self._sa_session.query(UserFileSource).filter(UserFileSource.user_id == trans.user.id).all()
        return [self._to_model(trans, s) for s in stores]

    def show(self, trans: ProvidesUserContext, uuid: UUID4) -> UserFileSourceModel:
        user_file_source = self._get(trans, uuid)
        return self._to_model(trans, user_file_source)

    def purge_instance(self, trans: ProvidesUserContext, uuid: UUID4) -> None:
        persisted_file_source = self._get(trans, uuid)
        purge_template_instance(trans, persisted_file_source, self._app_config)

    def modify_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: ModifyInstancePayload
    ) -> UserFileSourceModel:
        if isinstance(payload, UpgradeInstancePayload):
            return self._upgrade_instance(trans, id, payload)
        elif isinstance(payload, UpdateInstanceSecretPayload):
            return self._update_instance_secret(trans, id, payload)
        else:
            assert isinstance(payload, UpdateInstancePayload)
            return self._update_instance(trans, id, payload)

    def _upgrade_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpgradeInstancePayload
    ) -> UserFileSourceModel:
        persisted_file_source = self._get(trans, id)
        template = self._get_and_validate_target_upgrade_template(persisted_file_source, payload)
        persisted_file_source.template_version = template.version
        persisted_file_source.template_definition = template.model_dump()
        actual_variables = updated_template_variables(
            payload.variables,
            persisted_file_source,
            template,
        )
        persisted_file_source.template_variables = actual_variables
        upgrade_secrets(trans, persisted_file_source, template, payload, self._app_config)
        self._save(persisted_file_source)
        return self._to_model(trans, persisted_file_source)

    def _get_and_validate_target_upgrade_template(
        self, persisted_file_source: UserFileSource, payload: Union[UpgradeInstancePayload, TestUpgradeInstancePayload]
    ) -> FileSourceTemplate:
        template = self._get_template(persisted_file_source, payload.template_version)
        validate_no_extra_variables_defined(payload.variables, template)
        validate_no_extra_secrets_defined(payload.secrets, template)
        return template

    def _update_instance(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpdateInstancePayload
    ) -> UserFileSourceModel:
        persisted_file_source = self._get(trans, id)
        template = self._get_template(persisted_file_source)
        update_template_instance(self._sa_session, persisted_file_source, payload, template)
        return self._to_model(trans, persisted_file_source)

    def _update_instance_secret(
        self, trans: ProvidesUserContext, id: UUID4, payload: UpdateInstanceSecretPayload
    ) -> UserFileSourceModel:
        persisted_file_source = self._get(trans, id)
        template = self._get_template(persisted_file_source)
        update_instance_secret(trans, persisted_file_source, template, payload, self._app_config)
        return self._to_model(trans, persisted_file_source)

    def create_instance(self, trans: ProvidesUserContext, payload: CreateInstancePayload) -> UserFileSourceModel:
        catalog = self._catalog
        catalog.validate(payload)
        template = catalog.find_template(payload)
        assert template
        user_vault = trans.user_vault
        persisted_file_source = UserFileSource()
        persisted_file_source.user_id = trans.user.id
        assert persisted_file_source.user_id
        persisted_file_source.uuid = uuid4().hex
        persisted_file_source.template_definition = template.model_dump()
        persisted_file_source.template_id = template.id
        persisted_file_source.template_version = template.version
        persisted_file_source.template_variables = payload.variables
        persisted_file_source.name = payload.name
        persisted_file_source.description = payload.description
        self._save(persisted_file_source)

        # see big comment in object_store_instances around same block for some
        # notes about state handling here
        recorded_secrets = []
        try:
            for secret, value in payload.secrets.items():
                key = persisted_file_source.vault_key(secret, self._app_config)
                user_vault.write_secret(key, value)
                recorded_secrets.append(secret)
        except Exception:
            self._sa_session.delete(persisted_file_source)
            raise
        persisted_file_source.template_secrets = recorded_secrets
        self._save(persisted_file_source)
        return self._to_model(trans, persisted_file_source)

    def test_modify_instance(
        self, trans: ProvidesUserContext, id: str, payload: TestModifyInstancePayload
    ) -> PluginStatus:
        persisted_file_source = self._get(trans, id)
        if isinstance(payload, TestUpgradeInstancePayload):
            return self._plugin_status_for_upgrade(trans, payload, persisted_file_source)
        else:
            assert isinstance(payload, TestUpdateInstancePayload)
            return self._plugin_status_for_update(trans, payload, persisted_file_source)

    def _plugin_status_for_update(
        self, trans: ProvidesUserContext, payload: TestUpdateInstancePayload, persisted_file_source: UserFileSource
    ) -> PluginStatus:
        template = self._get_template(persisted_file_source)
        target = UpdateTestTarget(persisted_file_source, payload)
        return self._plugin_status_for_template(trans, target, template)

    def _plugin_status_for_upgrade(
        self, trans: ProvidesUserContext, payload: TestUpgradeInstancePayload, persisted_file_source: UserFileSource
    ) -> PluginStatus:
        template = self._get_and_validate_target_upgrade_template(persisted_file_source, payload)
        target = UpgradeTestTarget(persisted_file_source, payload)
        return self._plugin_status_for_template(trans, target, template)

    def plugin_status_for_instance(self, trans: ProvidesUserContext, id: str):
        persisted_file_source = self._get(trans, id)
        return self._plugin_status(trans, persisted_file_source, to_template_reference(persisted_file_source))

    def plugin_status(self, trans: ProvidesUserContext, payload: CreateInstancePayload) -> PluginStatus:
        return self._plugin_status(trans, payload, payload)

    def _plugin_status(
        self, trans: ProvidesUserContext, payload: CanTestPluginStatus, template_reference: TemplateReference
    ):
        template = self._catalog.find_template(template_reference)
        return self._plugin_status_for_template(trans, payload, template)

    def _plugin_status_for_template(
        self, trans: ProvidesUserContext, payload: CanTestPluginStatus, template: FileSourceTemplate
    ):
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
        file_source, connection_status = self._connection_status(trans, payload, configuration)
        status_kwds["connection"] = connection_status
        if connection_status.is_not_ok:
            return PluginStatus(**status_kwds)
        assert file_source
        # Lets circle back to this - we need to add an entry point to the file source plugins
        # to test if things are writable. We could ping remote APIs or do something like os.access('/path/to/folder', os.W_OK)
        # locally.
        return PluginStatus(**status_kwds)

    def _template_settings_status(
        self,
        trans: ProvidesUserContext,
        payload: CanTestPluginStatus,
        template: FileSourceTemplate,
    ) -> Tuple[Optional[FileSourceConfiguration], PluginAspectStatus]:
        template_parameters = prepare_template_parameters_for_testing(
            trans, template, payload, self._app_vault, self._app_config
        )
        configuration = None
        exception = None
        try:
            configuration = template_to_configuration(template, **template_parameters)
        except Exception as e:
            exception = e
        return configuration, settings_exception_to_status(exception)

    def _connection_status(
        self, trans: ProvidesUserContext, payload: CanTestPluginStatus, configuration: FileSourceConfiguration
    ) -> Tuple[Optional[BaseFilesSource], PluginAspectStatus]:
        file_source = None
        exception = None
        if isinstance(payload, (UpgradeTestTarget, UpdateTestTarget)):
            label = payload.instance.name
            doc = payload.instance.description
        else:
            label = payload.name
            doc = payload.description
        try:
            file_source_properties = configuration_to_file_source_properties(
                configuration,
                label=label,
                doc=doc,
                id=uuid4().hex,
            )
            file_source = self._resolver._file_source(file_source_properties)
            if hasattr(file_source, "list"):
                assert file_source
                # if we can list the root, do that and assume there is
                # a connection problem if we cannot
                browsable_file_source = cast(SupportsBrowsing, file_source)
                user_context = ProvidesFileSourcesUserContext(trans)
                browsable_file_source.list("/", recursive=False, user_context=user_context)
        except Exception as e:
            exception = e
        return file_source, connection_exception_to_status("file source", exception)

    def _index_filter(self, uuid: UUID4):
        return UserFileSource.__table__.c.uuid == uuid

    def _get(self, trans: ProvidesUserContext, uuid: UUID4) -> UserFileSource:
        filter = self._index_filter(uuid)
        user_file_source = self._sa_session.query(UserFileSource).filter(filter).one_or_none()
        if user_file_source is None:
            raise RequestParameterInvalidException(f"Failed to fetch object store for id {id}")
        if user_file_source.user != trans.user:
            raise ItemOwnershipException()
        return user_file_source

    def _get_template(
        self, persisted_object_store: UserFileSource, template_version: Optional[int] = None
    ) -> FileSourceTemplate:
        catalog = self._catalog
        target_template_version = template_version or persisted_object_store.template_version
        template = catalog.find_template_by(persisted_object_store.template_id, target_template_version)
        return template

    def _save(self, user_file_source: UserFileSource) -> None:
        save_template_instance(self._sa_session, user_file_source)

    def _to_model(self, trans, persisted_file_source: UserFileSource) -> UserFileSourceModel:
        file_source_type = persisted_file_source.template.configuration.type
        secrets = persisted_file_source.template_secrets or []
        uuid = str(persisted_file_source.uuid)
        uri_root = f"{USER_FILE_SOURCES_SCHEME}://{uuid}"
        return UserFileSourceModel(
            uuid=uuid,
            uri_root=uri_root,
            type=file_source_type,
            template_id=persisted_file_source.template_id,
            template_version=persisted_file_source.template_version,
            variables=persisted_file_source.template_variables,
            secrets=secrets,
            name=persisted_file_source.name,
            description=persisted_file_source.description,
            hidden=persisted_file_source.hidden,
            active=persisted_file_source.active,
            purged=persisted_file_source.purged,
        )


class UserDefinedFileSourcesImpl(UserDefinedFileSources):
    _sa_session: galaxy_scoped_session
    _app_config: UserDefinedFileSourcesConfig
    _file_sources_config: FileSourcePluginsConfig
    _plugin_loader: FileSourcePluginLoader
    _app_vault: Vault

    def __init__(
        self,
        sa_session: galaxy_scoped_session,
        app_config: UserDefinedFileSourcesConfig,
        file_sources_config: FileSourcePluginsConfig,
        plugin_loader: FileSourcePluginLoader,
        vault: Vault,
        catalog: ConfiguredFileSourceTemplates,
    ):
        self._sa_session = sa_session
        self._app_config = app_config
        self._plugin_loader = plugin_loader
        self._file_sources_config = file_sources_config
        self._app_vault = vault
        self._catalog = catalog

    def _user_file_source(self, uri: str) -> Optional[UserFileSource]:
        if "://" not in uri:
            return None
        uri_scheme, uri_rest = uri.split("://", 1)
        if uri_scheme != USER_FILE_SOURCES_SCHEME:
            return None
        if "/" in uri_rest:
            uri_root, _ = uri_rest.split("/", 1)
        else:
            uri_root = uri_rest
        index_filter = UserFileSource.__table__.c.uuid == uri_root
        user_object_store: UserFileSource = self._sa_session.query(UserFileSource).filter(index_filter).one()
        return user_object_store

    def _file_source_properties_from_uri(self, uri: str) -> Optional[FilesSourceProperties]:
        user_file_source = self._user_file_source(uri)
        if not user_file_source:
            return None
        if not user_file_source.active:
            return None
        return self._file_source_properties(user_file_source)

    def _file_source_properties(self, user_file_source: UserFileSource) -> FilesSourceProperties:
        secrets = recover_secrets(user_file_source, self._app_vault, self._app_config)
        environment = prepare_environment(user_file_source, self._app_vault, self._app_config)
        templates = sort_templates(
            self._app_config,
            self._catalog.catalog.root,
            user_file_source,
        )
        file_source_configuration: FileSourceConfiguration = user_file_source.file_source_configuration(
            secrets=secrets, environment=environment, templates=templates
        )
        return configuration_to_file_source_properties(
            file_source_configuration,
            label=user_file_source.name,
            doc=user_file_source.description,
            id=f"{user_file_source.uuid}",
        )

    def validate_uri_root(self, uri: str, user_context: FileSourcesUserContext) -> None:
        user_object_store = self._user_file_source(uri)
        if not user_object_store:
            return
        if user_object_store.user.username != user_context.username:
            raise ItemOwnershipException("Your Galaxy user does not have access to the requested resource.")

    def find_best_match(self, url: str) -> Optional[FileSourceScore]:
        files_source_properties = self._file_source_properties_from_uri(url)
        if files_source_properties is None:
            return None
        file_source = self._file_source(files_source_properties)
        return FileSourceScore(file_source, len(url))

    def _file_source(self, files_source_properties: FilesSourceProperties) -> BaseFilesSource:
        plugin_source = plugin_source_from_dict([cast(Dict[str, Any], files_source_properties)])
        file_source = self._plugin_loader.load_plugins(
            plugin_source,
            self._file_sources_config,
        )[0]
        return file_source

    def _all_user_file_source_properties(self, user_context: FileSourcesUserContext) -> List[FilesSourceProperties]:
        username_filter = User.__table__.c.username == user_context.username
        user: Optional[User] = self._sa_session.query(User).filter(username_filter).one_or_none()
        if user is None:
            return []
        all_file_source_properties: List[FilesSourceProperties] = []
        for user_file_source in user.file_sources:
            if user_file_source.hidden:
                continue
            try:
                files_source_properties = self._file_source_properties(user_file_source)
            except ValidationError:
                log.warning(f"Problem validating user_file_source {user_file_source.uuid}, skipping load.")
                continue
            all_file_source_properties.append(files_source_properties)
        return all_file_source_properties

    def user_file_sources_to_dicts(
        self,
        for_serialization: bool,
        user_context: FileSourcesUserContext,
        browsable_only: Optional[bool] = False,
        include_kind: Optional[Set[PluginKind]] = None,
        exclude_kind: Optional[Set[PluginKind]] = None,
    ) -> List[FilesSourceProperties]:
        """Write out user file sources as list of config dictionaries."""
        if user_context.anonymous:
            return []

        as_dicts = []
        for files_source_properties in self._all_user_file_source_properties(user_context):
            plugin_kind = PluginKind.rfs
            if include_kind and plugin_kind not in include_kind:
                continue
            if exclude_kind and plugin_kind in exclude_kind:
                continue
            files_source_type = files_source_properties["type"]
            is_browsable = file_source_type_is_browsable(self._plugin_loader.get_plugin_type_class(files_source_type))
            if browsable_only and not is_browsable:
                continue
            file_source = self._file_source(files_source_properties)
            as_dicts.append(file_source.to_dict(for_serialization=for_serialization, user_context=user_context))
        return as_dicts


# Turn the validated Pydantic thing describe what is possible to configure to the
# raw TypedDict consumed by the actual galaxy.files plugins.
def configuration_to_file_source_properties(
    file_source_configuration: FileSourceConfiguration,
    label: str,
    doc: Optional[str],
    id: str,
) -> FilesSourceProperties:
    file_source_properties = cast(FilesSourceProperties, file_source_configuration.model_dump())
    file_source_properties["label"] = label
    file_source_properties["doc"] = doc
    file_source_properties["id"] = id
    file_source_properties["scheme"] = USER_FILE_SOURCES_SCHEME
    # Moved this into templates - plugins should just define this and decide what
    # that looks like. aws public buckets are clearly not writable, private buckets
    # maybe should give users the option, etc..
    # file_source_properties["writable"] = True

    # We did templating with Jinja - disable Galaxy's Cheetah templating for
    # these plugins. I can't imagine a use case for that and I would hate to templating
    # languages having odd interactions.
    file_source_properties["disable_templating"] = True
    return file_source_properties


__all__ = (
    "CreateInstancePayload",
    "FileSourceInstancesManager",
    "ModifyInstancePayload",
    "TestModifyInstancePayload",
    "TestUpgradeInstancePayload",
    "TestUpdateInstancePayload",
    "UpdateInstancePayload",
    "UpdateInstanceSecretPayload",
    "UpgradeInstancePayload",
    "UserDefinedFileSourcesImpl",
    "UserFileSourceModel",
    "FileSourceInstancesManager",
    "UserDefinedFileSourcesConfig",
)
