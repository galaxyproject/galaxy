"""
API operations on User objects.
"""

import copy
import json
import logging
import re
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from markupsafe import escape
from typing_extensions import Annotated

from galaxy import (
    exceptions,
    util,
)
from galaxy.exceptions import ObjectInvalid
from galaxy.managers import users
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.model import (
    FormDefinition,
    HistoryDatasetAssociation,
    Role,
    UserAddress,
    UserObjectstoreUsage,
    UserQuotaUsage,
)
from galaxy.model.base import transaction
from galaxy.schema import APIKeyModel
from galaxy.schema.schema import (
    AnonUserModel,
    AsyncTaskResultSummary,
    CreatedUserModel,
    CustomBuildCreationPayload,
    CustomBuildsCollection,
    DeletedCustomBuild,
    DetailedUserModel,
    FavoriteObject,
    FavoriteObjectsSummary,
    FavoriteObjectType,
    FlexibleUserIdType,
    MaybeLimitedUserModel,
    RemoteUserCreationPayload,
    RoleListResponse,
    UserBeaconSetting,
    UserCreationPayload,
    UserDeletionPayload,
    UserUpdatePayload,
)
from galaxy.security.validate_user_input import (
    validate_email,
    validate_password,
    validate_publicname,
)
from galaxy.security.vault import UserVaultWrapper
from galaxy.tool_util.toolbox.filters import FilterFactory
from galaxy.util import (
    docstring_trim,
    listify,
)
from galaxy.web import expose_api
from galaxy.web.form_builder import AddressField
from galaxy.webapps.base.controller import (
    BaseUIController,
    UsesFormDefinitionsMixin,
    UsesTagsMixin,
)
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import UserIdPathParam
from galaxy.webapps.galaxy.services.users import UsersService

log = logging.getLogger(__name__)

router = Router(tags=["users"])

ThemePathParam: str = Path(default=..., title="Theme", description="The theme of the GUI")
UserDeletedQueryParam: bool = Query(default=None, title="Deleted user", description="Indicates if the user is deleted")
UsersDeletedQueryParam: bool = Query(
    default=False, title="Deleted users", description="Indicates if the collection will be about deleted users"
)
FilterEmailQueryParam: str = Query(default=None, title="Email filter", description="An email address to filter on")
FilterNameQueryParam: str = Query(default=None, title="Name filter", description="An username address to filter on")
FilterAnyQueryParam: str = Query(default=None, title="Any filter", description="Filter on username OR email")
FlexibleUserIdPathParam: FlexibleUserIdType = Path(
    ..., title="User ID", description="The ID of the user to get or 'current'."
)
QuotaSourceLabelPathParam: str = Path(
    ...,
    title="Quota Source Label",
    description="The label corresponding to the quota source to fetch usage information about.",
)
ObjectTypePathParam: FavoriteObjectType = Path(
    default=..., title="Object type", description="The object type the user wants to favorite"
)
ObjectIDPathParam: str = Path(
    default=...,
    title="Object ID",
    description="The ID of an object the user wants to remove from favorites",
)
CustomBuildKeyPathParam: str = Path(
    default=...,
    title="Custom build key",
    description="The key of the custom build to be deleted.",
)

RecalculateDiskUsageSummary = "Triggers a recalculation of the current user disk usage."
RecalculateDiskUsageResponseDescriptions = {
    200: {
        "model": AsyncTaskResultSummary,
        "description": "The asynchronous task summary to track the task state.",
    },
    204: {
        "description": "The background task was submitted but there is no status tracking ID available.",
    },
}

UserUpdateBody = Body(default=..., title="Update user", description="The user values to update.")
FavoriteObjectBody = Body(
    default=..., title="Set favorite", description="The id of an object the user wants to favorite."
)

CustomBuildCreationBody = Body(
    default=..., title="Add custom build", description="The values to add a new custom build."
)
UserCreationBody = Body(default=..., title="Create User", description="The values to add create a user.")
AnyUserModel = Union[DetailedUserModel, AnonUserModel]


@router.cbv
class FastAPIUsers:
    service: UsersService = depends(UsersService)
    user_serializer: users.UserSerializer = depends(users.UserSerializer)

    @router.put(
        "/api/users/current/recalculate_disk_usage",
        summary=RecalculateDiskUsageSummary,
        responses=RecalculateDiskUsageResponseDescriptions,
    )
    @router.put(
        "/api/users/recalculate_disk_usage",
        summary=RecalculateDiskUsageSummary,
        responses=RecalculateDiskUsageResponseDescriptions,
        deprecated=True,
    )
    def recalculate_disk_usage(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """This route will be removed in a future version.

        Please use `/api/users/current/recalculate_disk_usage` instead.
        """
        user_id = getattr(trans.user, "id", None)
        if not user_id:
            raise exceptions.AuthenticationRequired("Only registered users can recalculate disk usage.")
        else:
            result = self.service.recalculate_disk_usage(trans, user_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT) if result is None else result

    @router.put(
        "/api/users/{user_id}/recalculate_disk_usage",
        summary=RecalculateDiskUsageSummary,
        responses=RecalculateDiskUsageResponseDescriptions,
        require_admin=True,
    )
    def recalculate_disk_usage_by_user_id(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        result = self.service.recalculate_disk_usage(trans, user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT) if result is None else result

    @router.get(
        "/api/users/deleted",
        name="get_deleted_users",
        description="Return a collection of deleted users. Only admins can see deleted users.",
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        f_email: Optional[str] = FilterEmailQueryParam,
        f_name: Optional[str] = FilterNameQueryParam,
        f_any: Optional[str] = FilterAnyQueryParam,
    ) -> List[MaybeLimitedUserModel]:
        return self.service.get_index(trans=trans, deleted=True, f_email=f_email, f_name=f_name, f_any=f_any)

    @router.post(
        "/api/users/deleted/{user_id}/undelete",
        name="undelete_user",
        summary="Restore a deleted user. Only admins can restore users.",
        require_admin=True,
    )
    def undelete(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> DetailedUserModel:
        user = self.service.get_user(trans=trans, user_id=user_id)
        self.service.user_manager.undelete(user)
        return self.service.user_to_detailed_model(user)

    @router.get(
        "/api/users/deleted/{user_id}",
        name="get_deleted_user",
        summary="Return information about a deleted user. Only admins can see deleted users.",
    )
    def show_deleted(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> AnyUserModel:
        return self.service.show_user(trans=trans, user_id=user_id, deleted=True)

    @router.get(
        "/api/users/{user_id}/api_key",
        name="get_or_create_api_key",
        summary="Return the user's API key",
    )
    def get_or_create_api_key(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> str:
        return self.service.get_or_create_api_key(trans, user_id)

    @router.get(
        "/api/users/{user_id}/api_key/detailed",
        name="get_api_key_detailed",
        summary="Return the user's API key with extra information.",
        responses={
            200: {
                "model": APIKeyModel,
                "description": "The API key of the user.",
            },
            204: {
                "description": "The user doesn't have an API key.",
            },
        },
    )
    def get_api_key(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        api_key = self.service.get_api_key(trans, user_id)
        return api_key if api_key else Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/api/users/{user_id}/api_key", name="create_api_key", summary="Create a new API key for the user")
    def create_api_key(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> str:
        return self.service.create_api_key(trans, user_id).key

    @router.delete(
        "/api/users/{user_id}/api_key",
        name="delete_api_key",
        summary="Delete the current API key of the user",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_api_key(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.delete_api_key(trans, user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/users/{user_id}/usage",
        name="get_user_usage",
        summary="Return the user's quota usage summary broken down by quota source",
    )
    def usage(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_id: FlexibleUserIdType = FlexibleUserIdPathParam,
    ) -> List[UserQuotaUsage]:
        if user := self.service.get_user_full(trans, user_id, False):
            rval = self.user_serializer.serialize_disk_usage(user)
            return rval
        else:
            return []

    @router.get(
        "/api/users/{user_id}/objectstore_usage",
        name="get_user_objectstore_usage",
        summary="Return the user's object store usage summary broken down by object store ID",
    )
    def objectstore_usage(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_id: FlexibleUserIdType = FlexibleUserIdPathParam,
    ) -> List[UserObjectstoreUsage]:
        if user := self.service.get_user_full(trans, user_id, False):
            return user.dictify_objectstore_usage()
        else:
            return []

    @router.get(
        "/api/users/{user_id}/usage/{label}",
        name="get_user_usage_for_label",
        summary="Return the user's quota usage summary for a given quota source label",
    )
    def usage_for(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_id: FlexibleUserIdType = FlexibleUserIdPathParam,
        label: str = QuotaSourceLabelPathParam,
    ) -> Optional[UserQuotaUsage]:
        effective_label: Optional[str] = label
        if label == "__null__":
            effective_label = None
        if user := self.service.get_user_full(trans, user_id, False):
            rval = self.user_serializer.serialize_disk_usage_for(user, effective_label)
            return rval
        else:
            return None

    @router.get(
        "/api/users/{user_id}/beacon",
        name="get_beacon_settings",
        summary="Return information about beacon share settings",
    )
    def get_beacon(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> UserBeaconSetting:
        """
        **Warning**: This endpoint is experimental and might change or disappear in future versions.
        """
        user = self.service.get_user(trans, user_id)

        enabled = user.preferences["beacon_enabled"] if "beacon_enabled" in user.preferences else False

        return UserBeaconSetting(enabled=enabled)

    @router.post(
        "/api/users/{user_id}/beacon",
        name="set_beacon_settings",
        summary="Change beacon setting",
    )
    def set_beacon(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UserBeaconSetting = Body(...),
    ) -> UserBeaconSetting:
        """
        **Warning**: This endpoint is experimental and might change or disappear in future versions.
        """
        user = self.service.get_user(trans, user_id)

        user.preferences["beacon_enabled"] = payload.enabled
        with transaction(trans.sa_session):
            trans.sa_session.commit()

        return payload

    @router.delete(
        "/api/users/{user_id}/favorites/{object_type}/{object_id:path}",
        name="remove_favorite",
        summary="Remove the object from user's favorites",
    )
    def remove_favorite(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        object_type: FavoriteObjectType = ObjectTypePathParam,
        object_id: str = ObjectIDPathParam,
    ) -> FavoriteObjectsSummary:
        user = self.service.get_user(trans, user_id)
        favorites = json.loads(user.preferences["favorites"]) if "favorites" in user.preferences else {}
        if object_type.value == "tools":
            favorite_tools = favorites.get("tools", [])
            if object_id in favorite_tools:
                del favorite_tools[favorite_tools.index(object_id)]
                favorites["tools"] = favorite_tools
                user.preferences["favorites"] = json.dumps(favorites)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            else:
                raise exceptions.ObjectNotFound("Given object is not in the list of favorites")
        return FavoriteObjectsSummary.model_validate(favorites)

    @router.put(
        "/api/users/{user_id}/favorites/{object_type}",
        name="set_favorite",
        summary="Add the object to user's favorites",
    )
    def set_favorite(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        object_type: FavoriteObjectType = ObjectTypePathParam,
        payload: FavoriteObject = FavoriteObjectBody,
    ) -> FavoriteObjectsSummary:
        user = self.service.get_user(trans, user_id)
        favorites = json.loads(user.preferences["favorites"]) if "favorites" in user.preferences else {}
        if object_type.value == "tools":
            tool_id = payload.object_id
            tool = trans.app.toolbox.get_tool(tool_id)
            if not tool:
                raise exceptions.ObjectNotFound(f"Could not find tool with id '{tool_id}'.")
            if not tool.allow_user_access(user):
                raise exceptions.AuthenticationFailed(f"Access denied for tool with id '{tool_id}'.")
            favorite_tools = favorites.get("tools", [])
            if tool_id not in favorite_tools:
                favorite_tools.append(tool_id)
                favorites["tools"] = favorite_tools
                user.preferences["favorites"] = json.dumps(favorites)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
        return FavoriteObjectsSummary.model_validate(favorites)

    @router.put(
        "/api/users/{user_id}/theme/{theme}",
        name="set_theme",
        summary="Set the user's theme choice",
    )
    def set_theme(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        theme: str = ThemePathParam,
    ) -> str:
        user = self.service.get_user(trans, user_id)
        user.preferences["theme"] = theme
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return theme

    @router.put(
        "/api/users/{user_id}/custom_builds/{key}",
        name="add_custom_builds",
        summary="Add new custom build.",
    )
    def add_custom_builds(
        self,
        user_id: UserIdPathParam,
        key: str = CustomBuildKeyPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CustomBuildCreationPayload = CustomBuildCreationBody,
    ) -> Any:
        user = self.service.get_user(trans, user_id)
        dbkeys = json.loads(user.preferences["dbkeys"]) if "dbkeys" in user.preferences else {}
        name = payload.name
        len_type = payload.len_type
        len_value = payload.len_value
        if len_type not in ["file", "fasta", "text"] or not len_value:
            raise exceptions.RequestParameterInvalidException("Please specify a valid data source type.")
        if not name or not key:
            raise exceptions.RequestParameterMissingException("You must specify values for all the fields.")
        elif key in dbkeys:
            raise exceptions.DuplicatedIdentifierException(
                "There is already a custom build with that key. Delete it first if you want to replace it."
            )
        else:
            # Have everything needed; create new build.
            build_dict = {"name": name}
            if len_type in ["text", "file"]:
                # Create new len file
                new_len = trans.app.model.HistoryDatasetAssociation(
                    extension="len", create_dataset=True, sa_session=trans.sa_session
                )
                trans.sa_session.add(new_len)
                new_len.name = name
                new_len.visible = False
                new_len.state = trans.app.model.Job.states.OK
                new_len.info = "custom build .len file"
                try:
                    trans.app.object_store.create(new_len.dataset)
                except ObjectInvalid:
                    raise exceptions.InternalServerError("Unable to create output dataset: object store is full.")
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                counter = 0
                lines_skipped = 0
                with open(new_len.get_file_name(), "w") as f:
                    # LEN files have format:
                    #   <chrom_name><tab><chrom_length>
                    for line in len_value.split("\n"):
                        # Splits at the last whitespace in the line
                        lst = line.strip().rsplit(None, 1)
                        if not lst or len(lst) < 2:
                            lines_skipped += 1
                            continue
                        # TODO Does name length_str fit here?
                        chrom, length_str = lst[0], lst[1]
                        try:
                            length = int(length_str)
                        except ValueError:
                            lines_skipped += 1
                            continue
                        if chrom != escape(chrom):
                            build_dict["message"] = "Invalid chromosome(s) with HTML detected and skipped."
                            lines_skipped += 1
                            continue
                        counter += 1
                        f.write(f"{chrom}\t{length}\n")
                build_dict["len"] = new_len.id
                build_dict["count"] = str(counter)
            else:
                build_dict["fasta"] = trans.security.decode_id(len_value)
                dataset = trans.sa_session.get(HistoryDatasetAssociation, int(build_dict["fasta"]))
                assert dataset
                try:
                    new_len = dataset.get_converted_dataset(trans, "len")
                    new_linecount = new_len.get_converted_dataset(trans, "linecount")
                    build_dict["len"] = new_len.id
                    build_dict["linecount"] = new_linecount.id
                except Exception:
                    raise exceptions.ToolExecutionError("Failed to convert dataset.")
            dbkeys[key] = build_dict
            user.preferences["dbkeys"] = json.dumps(dbkeys)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/users/{user_id}/custom_builds", name="get_custom_builds", summary=" Returns collection of custom builds."
    )
    def get_custom_builds(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> CustomBuildsCollection:
        user = self.service.get_user(trans, user_id)
        dbkeys = json.loads(user.preferences["dbkeys"]) if "dbkeys" in user.preferences else {}
        valid_dbkeys = {}
        update = False
        for key, dbkey in dbkeys.items():
            if "count" not in dbkey and "linecount" in dbkey:
                chrom_count_dataset = trans.sa_session.get(HistoryDatasetAssociation, dbkey["linecount"])
                if (
                    chrom_count_dataset
                    and not chrom_count_dataset.deleted
                    and chrom_count_dataset.state == trans.app.model.HistoryDatasetAssociation.states.OK
                ):
                    chrom_count = int(open(chrom_count_dataset.get_file_name()).readline())
                    dbkey["count"] = chrom_count
                    valid_dbkeys[key] = dbkey
                    update = True
            else:
                valid_dbkeys[key] = dbkey
        if update:
            user.preferences["dbkeys"] = json.dumps(valid_dbkeys)
        dbkey_collection = []
        for key, attributes in valid_dbkeys.items():
            attributes["id"] = key
            dbkey_collection.append(attributes)
        return CustomBuildsCollection.model_construct(root=dbkey_collection)

    @router.delete(
        "/api/users/{user_id}/custom_builds/{key}", name="delete_custom_build", summary="Delete a custom build"
    )
    def delete_custom_builds(
        self,
        user_id: UserIdPathParam,
        key: str = CustomBuildKeyPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> DeletedCustomBuild:
        user = self.service.get_user(trans, user_id)
        dbkeys = json.loads(user.preferences["dbkeys"]) if "dbkeys" in user.preferences else {}
        if key and key in dbkeys:
            del dbkeys[key]
            user.preferences["dbkeys"] = json.dumps(dbkeys)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            return DeletedCustomBuild(message=f"Deleted {key}.")
        else:
            raise exceptions.ObjectNotFound(f"Could not find and delete build ({key}).")

    @router.post(
        "/api/users",
        name="create_user",
        summary="Create a new Galaxy user. Only admins can create users for now.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: Union[UserCreationPayload, RemoteUserCreationPayload] = UserCreationBody,
    ) -> CreatedUserModel:
        if isinstance(payload, UserCreationPayload):
            email = payload.email
            username = payload.username
            password = payload.password
        if isinstance(payload, RemoteUserCreationPayload):
            email = payload.remote_user_email
            username = ""
            password = ""
        if not trans.app.config.allow_user_creation and not trans.user_is_admin:
            raise exceptions.ConfigDoesNotAllowException("User creation is not allowed in this Galaxy instance")
        if trans.app.config.use_remote_user and trans.user_is_admin:
            user = self.service.user_manager.get_or_create_remote_user(remote_user_email=email)
        elif trans.user_is_admin:
            message = "\n".join(
                (
                    validate_email(trans, email),
                    validate_password(trans, password, password),
                    validate_publicname(trans, username),
                )
            ).rstrip()
            if message:
                raise exceptions.RequestParameterInvalidException(message)
            else:
                user = self.service.user_manager.create(email=email, username=username, password=password)
        else:
            raise exceptions.NotImplemented()
        item = user.to_dict(view="element", value_mapper={"total_disk_usage": float})
        return item

    @router.get(
        "/api/users",
        name="get_users",
        description="Return a collection of users. Filters will only work if enabled in config or user is admin.",
        response_model_exclude_unset=True,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = UsersDeletedQueryParam,
        f_email: Optional[str] = FilterEmailQueryParam,
        f_name: Optional[str] = FilterNameQueryParam,
        f_any: Optional[str] = FilterAnyQueryParam,
    ) -> List[MaybeLimitedUserModel]:
        return self.service.get_index(trans=trans, deleted=deleted, f_email=f_email, f_name=f_name, f_any=f_any)

    @router.get(
        "/api/users/{user_id}",
        name="get_user",
        summary="Return information about a specified or the current user. Only admin can see deleted or other users",
    )
    def show(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        user_id: FlexibleUserIdType = FlexibleUserIdPathParam,
        deleted: Optional[bool] = UserDeletedQueryParam,
    ) -> AnyUserModel:
        user_deleted = deleted or False
        return self.service.show_user(trans=trans, user_id=user_id, deleted=user_deleted)

    @router.put(
        "/api/users/{user_id}", name="update_user", summary="Update the values of a user. Only admin can update others."
    )
    def update(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user_id: FlexibleUserIdType = FlexibleUserIdPathParam,
        payload: UserUpdatePayload = UserUpdateBody,
        deleted: Optional[bool] = UserDeletedQueryParam,
    ) -> DetailedUserModel:
        deleted = deleted or False
        current_user = trans.user
        user_to_update = self.service.get_non_anonymous_user_full(trans, user_id, deleted=deleted)
        data = payload.model_dump(exclude_unset=True)
        self.service.user_deserializer.deserialize(user_to_update, data, user=current_user, trans=trans)
        return self.service.user_to_detailed_model(user_to_update)

    @router.delete(
        "/api/users/{user_id}",
        name="delete_user",
        summary="Delete a user. Only admins can delete others or purge users.",
    )
    def delete(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        purge: Annotated[
            bool,
            Query(
                title="Purge user",
                description="Whether to definitely remove this user. Only deleted users can be purged.",
            ),
        ] = False,
        payload: Optional[UserDeletionPayload] = None,
    ) -> DetailedUserModel:
        user_to_update = self.service.user_manager.by_id(user_id)
        purge = payload and payload.purge or purge
        if trans.user_is_admin:
            if purge:
                log.debug("Purging user %s", user_to_update)
                self.service.user_manager.purge(user_to_update)
            else:
                self.service.user_manager.delete(user_to_update)
        else:
            if trans.user == user_to_update:
                self.service.user_manager.delete(user_to_update)
            else:
                raise exceptions.InsufficientPermissionsException("You may only delete your own account.")
        return self.service.user_to_detailed_model(user_to_update)

    @router.post(
        "/api/users/{user_id}/send_activation_email",
        name="send_activation_email",
        summary="Sends activation email to user.",
        require_admin=True,
    )
    def send_activation_email(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        user = trans.sa_session.query(trans.model.User).get(user_id)
        if not user:
            raise exceptions.ObjectNotFound("User not found for given id.")
        if not self.service.user_manager.send_activation_email(trans, user.email, user.username):
            raise exceptions.MessageException("Unable to send activation email.")

    @router.get(
        "/api/users/{user_id}/roles",
        name="get user roles",
        description="Return a list of roles associated with this user. Only admins can see user roles.",
        require_admin=True,
    )
    def get_user_roles(
        self,
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RoleListResponse:
        return self.service.get_user_roles(trans=trans, user_id=user_id)


class UserAPIController(BaseGalaxyAPIController, UsesTagsMixin, BaseUIController, UsesFormDefinitionsMixin):
    service: UsersService = depends(UsersService)
    user_manager: users.UserManager = depends(users.UserManager)

    def _get_user_full(self, trans, user_id, **kwd):
        """Return referenced user or None if anonymous user is referenced."""
        deleted = kwd.get("deleted", "False")
        deleted = util.string_as_bool(deleted)
        return self.service.get_user_full(trans, user_id, deleted)

    def _get_extra_user_preferences(self, trans):
        """
        Reads the file user_preferences_extra_conf.yml to display
        admin defined user informations
        """
        return trans.app.config.user_preferences_extra["preferences"]

    def _build_extra_user_pref_inputs(self, trans, preferences, user):
        """
        Build extra user preferences inputs list.
        Add values to the fields if present
        """
        if not preferences:
            return []
        extra_pref_inputs = []
        # Build sections for different categories of inputs
        user_vault = UserVaultWrapper(trans.app.vault, user)
        for item, value in preferences.items():
            if value is not None:
                input_fields = copy.deepcopy(value["inputs"])
                for input in input_fields:
                    help = input.get("help", "")
                    required = "Required" if util.string_as_bool(input.get("required")) else ""
                    if help:
                        input["help"] = f"{help} {required}"
                    else:
                        input["help"] = required
                    if input.get("store") == "vault":
                        field = f"{item}/{input['name']}"
                        input["value"] = user_vault.read_secret(f"preferences/{field}")
                    else:
                        field = f"{item}|{input['name']}"
                        for data_item in user.extra_preferences:
                            if field in data_item:
                                input["value"] = user.extra_preferences[data_item]
                    # regardless of the store, do not send secret type values to client
                    if input.get("type") == "secret":
                        input["value"] = "__SECRET_PLACEHOLDER__"
                        # let the client treat it as a password field
                        input["type"] = "password"
                extra_pref_inputs.append(
                    {
                        "type": "section",
                        "title": value["description"],
                        "name": item,
                        "expanded": True,
                        "inputs": input_fields,
                    }
                )
        return extra_pref_inputs

    @expose_api
    def get_information(self, trans, id, **kwd):
        """
        GET /api/users/{id}/information/inputs
        Return user details such as username, email, addresses etc.

        :param id: the encoded id of the user
        :type  id: str
        """
        user = self._get_user(trans, id)
        email = user.email
        username = user.username
        inputs = []
        user_info = {
            "email": email,
            "username": username,
        }
        is_galaxy_app = trans.webapp.name == "galaxy"
        if (trans.app.config.enable_account_interface and not trans.app.config.use_remote_user) or not is_galaxy_app:
            inputs.append(
                {
                    "id": "email_input",
                    "name": "email",
                    "type": "text",
                    "label": "Email address",
                    "value": email,
                    "help": "If you change your email address you will receive an activation link in the new mailbox and you have to activate your account by visiting it.",
                }
            )
        if is_galaxy_app:
            if trans.app.config.enable_account_interface and not trans.app.config.use_remote_user:
                inputs.append(
                    {
                        "id": "name_input",
                        "name": "username",
                        "type": "text",
                        "label": "Public name",
                        "value": username,
                        "help": 'Your public name is an identifier that will be used to generate addresses for information you share publicly. Public names must be at least three characters in length and contain only lower-case letters, numbers, dots, underscores, and dashes (".", "_", "-").',
                    }
                )
            info_form_models = self.get_all_forms(
                trans, filter=dict(deleted=False), form_type=FormDefinition.types.USER_INFO
            )
            if info_form_models:
                info_form_id = trans.security.encode_id(user.values.form_definition.id) if user.values else None
                info_field = {
                    "type": "conditional",
                    "name": "info",
                    "cases": [],
                    "test_param": {
                        "name": "form_id",
                        "label": "User type",
                        "type": "select",
                        "value": info_form_id,
                        "help": "",
                        "data": [],
                    },
                }
                for f in info_form_models:
                    values = None
                    if info_form_id == trans.security.encode_id(f.id) and user.values:
                        values = user.values.content
                    info_form = f.populate(user=user, values=values, security=trans.security)
                    info_field["test_param"]["data"].append({"label": info_form["name"], "value": info_form["id"]})
                    info_field["cases"].append({"value": info_form["id"], "inputs": info_form["inputs"]})
                inputs.append(info_field)

            if trans.app.config.enable_account_interface:
                address_inputs = [{"type": "hidden", "name": "id", "hidden": True}]
                for field in AddressField.fields():
                    address_inputs.append({"type": "text", "name": field[0], "label": field[1], "help": field[2]})
                address_repeat = {
                    "title": "Address",
                    "name": "address",
                    "type": "repeat",
                    "inputs": address_inputs,
                    "cache": [],
                }
                address_values = [address.to_dict(trans) for address in user.addresses]
                for address in address_values:
                    address_cache = []
                    for input in address_inputs:
                        input_copy = input.copy()
                        input_copy["value"] = address.get(input["name"])
                        address_cache.append(input_copy)
                    address_repeat["cache"].append(address_cache)
                inputs.append(address_repeat)
                user_info["addresses"] = [address.to_dict(trans) for address in user.addresses]

            # Build input sections for extra user preferences
            extra_user_pref = self._build_extra_user_pref_inputs(trans, self._get_extra_user_preferences(trans), user)
            for item in extra_user_pref:
                inputs.append(item)
        else:
            if user.active_repositories:
                inputs.append(
                    dict(
                        id="name_input",
                        name="username",
                        label="Public name:",
                        type="hidden",
                        value=username,
                        help="You cannot change your public name after you have created a repository in this tool shed.",
                    )
                )
            else:
                inputs.append(
                    dict(
                        id="name_input",
                        name="username",
                        label="Public name:",
                        type="text",
                        value=username,
                        help='Your public name provides a means of identifying you publicly within this tool shed. Public names must be at least three characters in length and contain only lower-case letters, numbers, dots, underscores, and dashes (".", "_", "-"). You cannot change your public name after you have created a repository in this tool shed.',
                    )
                )
        user_info["inputs"] = inputs
        return user_info

    @expose_api
    def set_information(self, trans, id, payload=None, **kwd):
        """
        PUT /api/users/{id}/information/inputs
        Save a user's email, username, addresses etc.

        :param id: the encoded id of the user
        :type  id: str

        :param payload: data with new settings
        :type  payload: dict
        """
        payload = payload or {}
        user = self._get_user(trans, id)
        # Update email
        if "email" in payload:
            email = payload.get("email")
            message = validate_email(trans, email, user)
            if message:
                raise exceptions.RequestParameterInvalidException(message)
            if user.email != email:
                # Update user email and user's private role name which must match
                private_role = trans.app.security_agent.get_private_user_role(user)
                private_role.name = email
                private_role.description = f"Private role for {email}"
                user.email = email
                trans.sa_session.add(user)
                trans.sa_session.add(private_role)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                if trans.app.config.user_activation_on:
                    # Deactivate the user if email was changed and activation is on.
                    user.active = False
                    if self.user_manager.send_activation_email(trans, user.email, user.username):
                        message = "The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message."
                    else:
                        message = "Unable to send activation email, please contact your local Galaxy administrator."
                        if trans.app.config.error_email_to is not None:
                            message += f" Contact: {trans.app.config.error_email_to}"
                        raise exceptions.InternalServerError(message)
        # Update public name
        if "username" in payload:
            username = payload.get("username")
            message = validate_publicname(trans, username, user)
            if message:
                raise exceptions.RequestParameterInvalidException(message)
            if user.username != username:
                user.username = username
        # Update user custom form
        if user_info_form_id := payload.get("info|form_id"):
            prefix = "info|"
            user_info_form = trans.sa_session.get(FormDefinition, trans.security.decode_id(user_info_form_id))
            user_info_values = {}
            for item in payload:
                if item.startswith(prefix):
                    user_info_values[item[len(prefix) :]] = payload[item]
            form_values = trans.model.FormValues(user_info_form, user_info_values)
            trans.sa_session.add(form_values)
            user.values = form_values

        # Update values for extra user preference items
        extra_user_pref_data = {}
        extra_pref_keys = self._get_extra_user_preferences(trans)
        user_vault = UserVaultWrapper(trans.app.vault, user)
        current_extra_user_pref_data = json.loads(user.preferences.get("extra_user_preferences", "{}"))
        if extra_pref_keys is not None:
            for key in extra_pref_keys:
                key_prefix = f"{key}|"
                for item in payload:
                    if item.startswith(key_prefix):
                        keys = item.split("|")
                        section = extra_pref_keys[keys[0]]
                        matching_input = [input for input in section["inputs"] if input["name"] == keys[1]]
                        if matching_input:
                            input = matching_input[0]
                            if input.get("required") and payload[item] == "":
                                raise exceptions.ObjectAttributeMissingException("Please fill the required field")
                            input_type = input.get("type")
                            is_secret_value_unchanged = (
                                input_type == "secret" and payload[item] == "__SECRET_PLACEHOLDER__"
                            )
                            is_stored_in_vault = input.get("store") == "vault"
                            if is_secret_value_unchanged:
                                if not is_stored_in_vault:
                                    # If the value is unchanged, keep the current value
                                    extra_user_pref_data[item] = current_extra_user_pref_data.get(item, "")
                            else:
                                if is_stored_in_vault:
                                    user_vault.write_secret(f"preferences/{keys[0]}/{keys[1]}", str(payload[item]))
                                else:
                                    extra_user_pref_data[item] = payload[item]
                        else:
                            extra_user_pref_data[item] = payload[item]
            user.preferences["extra_user_preferences"] = json.dumps(extra_user_pref_data)

        # Update user addresses
        address_dicts = {}
        address_count = 0
        for item in payload:
            match = re.match(r"^address_(?P<index>\d+)\|(?P<attribute>\S+)", item)
            if match:
                groups = match.groupdict()
                index = int(groups["index"])
                attribute = groups["attribute"]
                address_dicts[index] = address_dicts.get(index) or {}
                address_dicts[index][attribute] = payload[item]
                address_count = max(address_count, index + 1)
        user.addresses = []
        for index in range(0, address_count):
            d = address_dicts[index]
            if d.get("id"):
                try:
                    user_address = trans.sa_session.get(UserAddress, trans.security.decode_id(d["id"]))
                except Exception as e:
                    raise exceptions.ObjectNotFound(f"Failed to access user address ({d['id']}). {e}")
            else:
                user_address = UserAddress()
                trans.log_event("User address added")
            for field in AddressField.fields():
                if str(field[2]).lower() == "required" and not d.get(field[0]):
                    raise exceptions.ObjectAttributeMissingException(
                        f"Address {index + 1}: {field[1]} ({field[0]}) required."
                    )
                setattr(user_address, field[0], str(d.get(field[0], "")))
            user_address.user = user
            user.addresses.append(user_address)
            trans.sa_session.add(user_address)
        trans.sa_session.add(user)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        trans.log_event("User information added")
        return {"message": "User information has been saved."}

    @expose_api
    def get_password(self, trans, id, payload=None, **kwd):
        """
        Return available password inputs.
        """
        payload = payload or {}
        return {
            "inputs": [
                {"name": "current", "type": "password", "label": "Current password"},
                {"name": "password", "type": "password", "label": "New password"},
                {"name": "confirm", "type": "password", "label": "Confirm password"},
            ]
        }

    @expose_api
    def set_password(self, trans, id, payload=None, **kwd):
        """
        Allows to the logged-in user to change own password.
        """
        payload = payload or {}
        user, message = self.user_manager.change_password(trans, id=id, **payload)
        if user is None:
            raise exceptions.AuthenticationRequired(message)
        return {"message": "Password has been changed."}

    @expose_api
    def get_permissions(self, trans, id, payload=None, **kwd):
        """
        Get the user's default permissions for the new histories
        """
        payload = payload or {}
        user = self._get_user(trans, id)
        roles = user.all_roles()
        inputs = []
        for index, action in trans.app.model.Dataset.permitted_actions.items():
            inputs.append(
                {
                    "type": "select",
                    "multiple": True,
                    "optional": True,
                    "name": index,
                    "label": action.action,
                    "help": action.description,
                    "options": list({(r.name, r.id) for r in roles}),
                    "value": [a.role.id for a in user.default_permissions if a.action == action.action],
                }
            )
        return {"inputs": inputs}

    @expose_api
    def set_permissions(self, trans, id, payload=None, **kwd):
        """
        Set the user's default permissions for the new histories
        """
        payload = payload or {}
        user = self._get_user(trans, id)
        permissions = {}
        for index, action in trans.app.model.Dataset.permitted_actions.items():
            action_id = trans.app.security_agent.get_action(action.action).action
            permissions[action_id] = [trans.sa_session.get(Role, x) for x in (payload.get(index) or [])]
        trans.app.security_agent.user_set_default_permissions(user, permissions)
        return {"message": "Permissions have been saved."}

    @expose_api
    def get_toolbox_filters(self, trans, id, payload=None, **kwd):
        """
        API call for fetching toolbox filters data. Toolbox filters are specified in galaxy.ini.
        The user can activate them and the choice is stored in user_preferences.
        """
        payload = payload or {}
        user = self._get_user(trans, id)
        filter_types = self._get_filter_types(trans)
        saved_values = {}
        for name, value in user.preferences.items():
            if name in filter_types:
                saved_values[name] = listify(value, do_strip=True)
        inputs = [
            {
                "type": "hidden",
                "name": "helptext",
                "label": "In this section you may enable or disable Toolbox filters. Please contact your admin to configure filters as necessary.",
            }
        ]
        errors = {}
        factory = FilterFactory(trans.app.toolbox)
        for filter_type in filter_types:
            self._add_filter_inputs(factory, filter_types, inputs, errors, filter_type, saved_values)
        return {"inputs": inputs, "errors": errors}

    @expose_api
    def set_toolbox_filters(self, trans, id, payload=None, **kwd):
        """
        API call to update toolbox filters data.
        """
        payload = payload or {}
        user = self._get_user(trans, id)
        filter_types = self._get_filter_types(trans)
        for filter_type in filter_types:
            new_filters = []
            for prefixed_name in payload:
                if prefixed_name.startswith(filter_type):
                    filter_selection = payload.get(prefixed_name)
                    if not isinstance(filter_selection, bool):
                        raise exceptions.RequestParameterInvalidException(
                            "Please specify the filter selection as boolean value."
                        )
                    if filter_selection:
                        prefix = f"{filter_type}|"
                        new_filters.append(prefixed_name[len(prefix) :])
            user.preferences[filter_type] = ",".join(new_filters)
        trans.sa_session.add(user)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return {"message": "Toolbox filters have been saved."}

    def _add_filter_inputs(self, factory, filter_types, inputs, errors, filter_type, saved_values):
        filter_inputs = []
        filter_values = saved_values.get(filter_type, [])
        filter_config = filter_types[filter_type]["config"]
        filter_title = filter_types[filter_type]["title"]
        for filter_name in filter_config:
            function = factory.build_filter_function(filter_name)
            if function is None:
                errors[f"{filter_type}|{filter_name}"] = "Filter function not found."

            short_description, description = None, None
            doc_string = docstring_trim(function.__doc__)
            split = doc_string.split("\n\n")
            if split:
                short_description = split[0]
                if len(split) > 1:
                    description = split[1]
            else:
                log.warning(f"No description specified in the __doc__ string for {filter_name}.")

            filter_inputs.append(
                {
                    "type": "boolean",
                    "name": filter_name,
                    "label": short_description or filter_name,
                    "help": description or "No description available.",
                    "value": True if filter_name in filter_values else False,
                }
            )
        if filter_inputs:
            inputs.append(
                {
                    "type": "section",
                    "title": filter_title,
                    "name": filter_type,
                    "expanded": True,
                    "inputs": filter_inputs,
                }
            )

    def _get_filter_types(self, trans):
        return {
            "toolbox_tool_filters": {"title": "Tools", "config": trans.app.config.user_tool_filters},
            "toolbox_section_filters": {"title": "Sections", "config": trans.app.config.user_tool_section_filters},
            "toolbox_label_filters": {"title": "Labels", "config": trans.app.config.user_tool_label_filters},
        }

    def _get_user(self, trans, id):
        user = self.get_user(trans, id)
        if not user:
            raise exceptions.RequestParameterInvalidException("Invalid user id specified.")
        if user != trans.user and not trans.user_is_admin:
            raise exceptions.InsufficientPermissionsException("Access denied.")
        return user
