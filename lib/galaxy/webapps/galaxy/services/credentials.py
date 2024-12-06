from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    Credentials,
    UserCredentials,
)
from galaxy.model.base import transaction
from galaxy.schema.credentials import (
    CredentialResponse,
    CredentialsListResponse,
    CredentialsPayload,
    DeleteCredentialsResponse,
    UserCredentialsListResponse,
    VerifyCredentialsResponse,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.security.vault import UserVaultWrapper
from galaxy.structured_app import StructuredApp
from galaxy.webapps.galaxy.api.common import UserIdPathParam


class CredentialsService:
    """Interface/service object shared by controllers for interacting with credentials."""

    def __init__(self, app: StructuredApp) -> None:
        self._app = app

    def list_user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> UserCredentialsListResponse:
        """Lists all credentials the user has provided (credentials themselves are not included)."""
        service_reference = f"{source_type}|{source_id}".strip("|") if source_type else None
        user_credentials, credentials_dict = self._user_credentials(
            trans, user_id=user_id, service_reference=service_reference
        )
        user_credentials_list = [
            CredentialsListResponse(
                service_reference=sref,
                user_credentials_id=next(
                    (uc.id for uc in user_credentials if uc.service_reference == sref),
                    None,
                ),
                credentials=self._credentials_response(creds),
            )
            for sref, creds in credentials_dict.items()
        ]
        return UserCredentialsListResponse(root=user_credentials_list)

    def verify_service_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
    ) -> VerifyCredentialsResponse:
        """Verifies if credentials have been provided for a specific service (no credential data returned)."""
        _, credentials_dict = self._user_credentials(trans, user_id=user_id, user_credentials_id=user_credentials_id)
        return VerifyCredentialsResponse(exists=bool(credentials_dict))

    def verify_credentials(
        self,
        trans: ProvidesUserContext,
        user_credentials_id: DecodedDatabaseIdField,
        credentials_id: DecodedDatabaseIdField,
    ) -> VerifyCredentialsResponse:
        """Verifies if a credential have been provided (no credential data returned)."""
        credentials = self._credentials(trans, user_credentials_id=user_credentials_id, id=credentials_id)
        return VerifyCredentialsResponse(exists=bool(credentials))

    def provide_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CredentialsPayload,
    ) -> CredentialsListResponse:
        """Allows users to provide credentials for a secret/variable."""
        return self._create_user_credential(trans, user_id, payload)

    def update_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        credentials_id: DecodedDatabaseIdField,
        payload: CredentialsPayload,
    ) -> CredentialsListResponse:
        """Updates credentials for a specific secret/variable."""
        return self._create_user_credential(trans, user_id, payload, credentials_id)

    def delete_service_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
    ) -> DeleteCredentialsResponse:
        """Deletes all credentials for a specific service."""
        user_credentials, credentials_dict = self._user_credentials(
            trans, user_id=user_id, user_credentials_id=user_credentials_id
        )
        session = trans.sa_session
        for credentials in credentials_dict.values():
            for credential in credentials:
                session.delete(credential)
        for user_credential in user_credentials:
            session.delete(user_credential)
        with transaction(session):
            session.commit()
        return DeleteCredentialsResponse(deleted=True)

    def delete_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        user_credentials_id: DecodedDatabaseIdField,
        credentials_id: DecodedDatabaseIdField,
    ) -> DeleteCredentialsResponse:
        """Deletes a specific credential."""
        credentials = self._credentials(trans, user_credentials_id=user_credentials_id, id=credentials_id)
        session = trans.sa_session
        for credential in credentials:
            session.delete(credential)
        with transaction(session):
            session.commit()
        return DeleteCredentialsResponse(deleted=True)

    def _user_credentials(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        service_reference: Optional[str] = None,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
    ) -> Tuple[List[UserCredentials], Dict[str, List[Credentials]]]:
        if not trans.user_is_admin and (not trans.user or trans.user != user_id):
            raise exceptions.ItemOwnershipException(
                "Only admins and the user can manage their own credentials.", type="error"
            )
        query = trans.sa_session.query(UserCredentials).filter(UserCredentials.user_id == user_id)
        if service_reference:
            query = query.filter(UserCredentials.service_reference.startswith(service_reference))
        if user_credentials_id:
            query = query.filter(UserCredentials.id == user_credentials_id)
        user_credentials_list = query.all()
        credentials_dict = {}
        for user_credential in user_credentials_list:
            credentials_list = self._credentials(trans, user_credentials_id=user_credential.id)
            credentials_dict[user_credential.service_reference] = credentials_list
        return user_credentials_list, credentials_dict

    def _credentials(
        self,
        trans: ProvidesUserContext,
        user_credentials_id: Optional[DecodedDatabaseIdField] = None,
        id: Optional[DecodedDatabaseIdField] = None,
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> List[Credentials]:
        query = trans.sa_session.query(Credentials)
        if user_credentials_id:
            query = query.filter(Credentials.user_credentials_id == user_credentials_id)
        if id:
            query = query.filter(Credentials.id == id)
        if name:
            query = query.filter(Credentials.name == name)
        if type:
            query = query.filter(Credentials.type == type)
        return query.all()

    def _credentials_response(self, credentials_list: List[Credentials]) -> List[CredentialResponse]:
        return [
            CredentialResponse(
                id=credential.id,
                name=credential.name,
                type=credential.type,
            )
            for credential in credentials_list
        ]

    def _create_user_credential(
        self,
        trans: ProvidesUserContext,
        user_id: UserIdPathParam,
        payload: CredentialsPayload,
        credentials_id: Optional[DecodedDatabaseIdField] = None,
    ) -> CredentialsListResponse:
        service_reference = payload.service_reference
        user_credentials_list, credentials_dict = self._user_credentials(
            trans, user_id, service_reference=service_reference
        )
        user_credential = user_credentials_list[0] if user_credentials_list else None

        session = trans.sa_session

        if not user_credential:
            user_credential = UserCredentials(
                user_id=user_id,
                service_reference=service_reference,
            )
            session.add(user_credential)
            session.flush()

        user_credential_id = user_credential.id

        provided_credentials_list: List[Credentials] = []
        for credential_payload in payload.credentials:
            credential_name = credential_payload.name
            credential_type = credential_payload.type
            credential_value = credential_payload.value

            credential = next(
                (
                    cred
                    for sref, creds in credentials_dict.items()
                    if sref == service_reference
                    for cred in creds
                    if cred.name == credential_name and cred.type == credential_type
                ),
                None,
            )

            if not credential:
                credential = Credentials(
                    user_credentials_id=user_credential_id,
                    name=credential_name,
                    type=credential_type,
                )
            elif not credentials_id:
                raise exceptions.RequestParameterInvalidException(
                    f"Credential {service_reference}|{credential_name} already exists.", type="error"
                )
            if credential_type == "secret":
                user_vault = UserVaultWrapper(self._app.vault, trans.user)
                user_vault.write_secret(f"{service_reference}|{credential_name}", credential_value)
            elif credential_type == "variable":
                credential.value = credential_value
            provided_credentials_list.append(credential)
            session.add(credential)
        with transaction(session):
            session.commit()
        return CredentialsListResponse(
            service_reference=service_reference,
            user_credentials_id=user_credential_id,
            credentials=self._credentials_response(provided_credentials_list),
        )
