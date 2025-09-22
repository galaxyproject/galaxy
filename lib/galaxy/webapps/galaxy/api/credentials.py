"""
API operations on credentials (credentials and variables).
"""

import logging
from typing import (
    Optional,
    Union,
)

from fastapi import (
    Query,
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.credentials import (
    CreateSourceCredentialsPayload,
    ExtendedUserCredentialsListResponse,
    SelectServiceCredentialPayload,
    ServiceCredentialGroupPayload,
    ServiceCredentialGroupResponse,
    SOURCE_TYPE,
    UserServiceCredentialsListResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import FlexibleUserIdType
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.credentials import CredentialsService

log = logging.getLogger(__name__)

router = Router(tags=["users"])


@router.cbv
class FastAPICredentials:
    service: CredentialsService = depends(CredentialsService)

    @router.get(
        "/api/users/{user_id}/credentials",
        summary="Lists all credentials the user has provided",
    )
    def list_user_credentials(
        self,
        user_id: FlexibleUserIdType,
        trans: ProvidesUserContext = DependsOnTrans,
        source_type: Optional[SOURCE_TYPE] = Query(
            None,
            description="The type of source to filter by.",
        ),
        source_id: Optional[str] = Query(
            None,
            description="The ID of the source to filter by.",
        ),
        source_version: Optional[str] = Query(
            None,
            description="The version of the source to filter by. By default it is the latest version.",
        ),
        include_definition: bool = Query(
            False,
            description="Whether to include extended credential definition information.",
        ),
    ) -> Union[UserServiceCredentialsListResponse, ExtendedUserCredentialsListResponse]:
        return self.service.list_user_credentials(
            trans, user_id, source_type, source_id, source_version, include_definition
        )

    @router.post(
        "/api/users/{user_id}/credentials",
        summary="Allows users to provide credentials for a secret/variable",
    )
    def provide_credential(
        self,
        user_id: FlexibleUserIdType,
        payload: CreateSourceCredentialsPayload,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> ServiceCredentialGroupResponse:
        return self.service.provide_credential(trans, user_id, payload)

    @router.put(
        "/api/users/{user_id}/credentials/group/{group_id}",
        summary="Updates user credentials",
    )
    def update_user_credentials(
        self,
        user_id: FlexibleUserIdType,
        group_id: DecodedDatabaseIdField,
        payload: ServiceCredentialGroupPayload,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> ServiceCredentialGroupResponse:
        return self.service.update_user_credentials(trans, user_id, group_id, payload)

    @router.put(
        "/api/users/{user_id}/credentials",
        summary="Updates the current credentials group",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update_user_credentials_group(
        self,
        user_id: FlexibleUserIdType,
        payload: SelectServiceCredentialPayload,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.update_user_credentials_group(trans, user_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/users/{user_id}/credentials/{user_credentials_id}",
        summary="Deletes all credentials for a specific service",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_service_credentials(
        self,
        user_id: FlexibleUserIdType,
        user_credentials_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.delete_credentials(trans, user_id, user_credentials_id=user_credentials_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/users/{user_id}/credentials/{user_credentials_id}/{group_id}",
        summary="Deletes a specific credential",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_credentials(
        self,
        user_id: FlexibleUserIdType,
        user_credentials_id: DecodedDatabaseIdField,
        group_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.delete_credentials(trans, user_id, user_credentials_id=user_credentials_id, group_id=group_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
