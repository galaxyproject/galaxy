"""
API operations on credentials (credentials and variables).
"""

import logging
from typing import Optional

from fastapi import (
    Query,
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.credentials import (
    CredentialsPayload,
    SOURCE_TYPE,
    UpdateCredentialsPayload,
    UserCredentialCreateResponse,
    UserCredentialsListResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import UserIdPathParam
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
        user_id: UserIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        source_type: Optional[SOURCE_TYPE] = Query(
            None,
            description="The type of source to filter by.",
        ),
        source_id: Optional[str] = Query(
            None,
            description="The ID of the source to filter by.",
        ),
        group_name: Optional[str] = Query(
            None,
            description="The name of the group to filter by.",
        ),
    ) -> UserCredentialsListResponse:
        return self.service.list_user_credentials(trans, user_id, source_type, source_id, group_name)

    @router.post(
        "/api/users/{user_id}/credentials",
        summary="Allows users to provide credentials for a secret/variable",
    )
    def provide_credential(
        self,
        user_id: UserIdPathParam,
        payload: CredentialsPayload,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> UserCredentialCreateResponse:
        return self.service.provide_credential(trans, user_id, payload)

    # @router.put(
    #     "/api/users/{user_id}/credentials/{user_credentials_id}",
    #     summary="Updates credentials for a specific secret/variable",
    # )
    # def update_credential(
    #     self,
    #     user_id: UserIdPathParam,
    #     user_credentials_id: DecodedDatabaseIdField,
    #     payload: UpdateCredentialsPayload,
    #     trans: ProvidesUserContext = DependsOnTrans,
    # ) -> CredentialsListResponse:
    #     return self.service.update_credential(trans, user_id, user_credentials_id, payload)

    # @router.delete(
    #     "/api/users/{user_id}/credentials/{user_credentials_id}",
    #     summary="Deletes all credentials for a specific service",
    # )
    # def delete_service_credentials(
    #     self,
    #     user_id: UserIdPathParam,
    #     user_credentials_id: DecodedDatabaseIdField,
    #     trans: ProvidesUserContext = DependsOnTrans,
    # ):
    #     self.service.delete_service_credentials(trans, user_id, user_credentials_id)
    #     return Response(status_code=status.HTTP_204_NO_CONTENT)

    # @router.delete(
    #     "/api/users/{user_id}/credentials/{user_credentials_id}/{group_id}",
    #     summary="Deletes a specific credential",
    # )
    # def delete_credentials(
    #     self,
    #     user_id: UserIdPathParam,
    #     user_credentials_id: DecodedDatabaseIdField,
    #     group_id: DecodedDatabaseIdField,
    #     trans: ProvidesUserContext = DependsOnTrans,
    # ):
    #     self.service.delete_credentials(trans, user_id, user_credentials_id, group_id)
    #     return Response(status_code=status.HTTP_204_NO_CONTENT)
