"""
API operations on defining cloud authorizations.

Through means of cloud authorization a user is able to grant a Galaxy server a secure access to his/her
cloud-based resources without sharing his/her long-lasting credentials.

User provides a provider-specific configuration, which Galaxy users to request temporary credentials
from the provider to access the user's resources.
"""

import logging

from galaxy.exceptions import (
    ActionInputError,
    InternalServerError,
    MalformedId,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers import cloudauthzs
from galaxy.structured_app import StructuredApp
from galaxy.util import unicodify
from galaxy.web import expose_api
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class CloudAuthzController(BaseGalaxyAPIController):
    """
    RESTfull controller for defining cloud authorizations.
    """

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.cloudauthz_manager = cloudauthzs.CloudAuthzManager(app)
        self.cloudauthz_serializer = cloudauthzs.CloudAuthzsSerializer(app)
        self.cloudauthz_deserializer = cloudauthzs.CloudAuthzsDeserializer(app)

    @expose_api
    def index(self, trans, **kwargs):
        """
        GET /api/cloud/authz

        Lists all the cloud authorizations user has defined.

        :type  trans: galaxy.webapps.base.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :param kwargs: empty dict

        :rtype: list of dict
        :return: a list of cloud authorizations (each represented in key-value pair format) defined for the user.
        """
        rtv = []
        for cloudauthz in trans.user.cloudauthz:
            rtv.append(
                self.cloudauthz_serializer.serialize_to_view(
                    cloudauthz, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, "summary")
                )
            )
        return rtv

    @expose_api
    def create(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/authz
            Request to store the payload as a cloudauthz (cloud authorization) configuration for a user.

        :type  trans: galaxy.webapps.base.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type payload: dict
        :param payload: A dictionary structure containing the following keys:
            *   provider:       the cloud-based resource provider to which this configuration belongs to.

            *   config:         a dictionary containing all the configuration required to request temporary credentials
                                from the provider. See the following page for details:
                                https://galaxyproject.org/authnz/

            *   authn_id:       the (encoded) ID of a third-party authentication of a user. To have this ID, user must
                                have logged-in to this Galaxy server using third-party identity (e.g., Google), or has
                                associated his/her Galaxy account with a third-party OIDC-based identity. See this page:
                                https://galaxyproject.org/authnz/config/

            *   description:    [Optional] a brief description for this configuration.

        :param kwargs: empty dict

        :rtype: dict
        :return: a dictionary with the following kvp:
            *   status:     HTTP response code
            *   message:    A message complementary to the response code.
        """
        msg_template = f"Rejected user `{str(trans.user.id)}`'s request to create cloudauthz config because of {{}}."
        if not isinstance(payload, dict):
            raise ActionInputError(
                "Invalid payload data type. The payload is expected to be a dictionary, but "
                "received data of type `{}`.".format(str(type(payload)))
            )

        missing_arguments = []
        provider = payload.get("provider", None)
        if provider is None:
            missing_arguments.append("provider")

        config = payload.get("config", None)
        if config is None:
            missing_arguments.append("config")

        authn_id = payload.get("authn_id", None)
        if authn_id is None and provider.lower() not in ["azure", "gcp"]:
            missing_arguments.append("authn_id")

        if len(missing_arguments) > 0:
            log.debug(msg_template.format(f"missing required config {missing_arguments}"))
            raise RequestParameterMissingException(
                "The following required arguments are missing in the payload: " "{}".format(missing_arguments)
            )

        description = payload.get("description", "")

        if not isinstance(config, dict):
            log.debug(msg_template.format(f"invalid config type `{type(config)}`, expect `dict`"))
            raise RequestParameterInvalidException(
                "Invalid type for the required `config` variable; expect `dict` "
                "but received `{}`.".format(type(config))
            )
        if authn_id:
            try:
                decoded_authn_id = self.decode_id(authn_id)
            except MalformedId as e:
                log.debug(msg_template.format(f"cannot decode authz_id `{authn_id}`"))
                raise e

            try:
                trans.app.authnz_manager.can_user_assume_authn(trans, decoded_authn_id)
            except Exception as e:
                raise e

        # No two authorization configuration with
        # exact same key/value should exist.
        for ca in trans.user.cloudauthz:
            if ca.equals(trans.user.id, provider, authn_id, config):
                log.debug(
                    "Rejected user `{}`'s request to create cloud authorization because a similar config "
                    "already exists.".format(trans.user.id)
                )
                raise ActionInputError("A similar cloud authorization configuration is already defined.")

        try:
            new_cloudauthz = self.cloudauthz_manager.create(
                user_id=trans.user.id, provider=provider, config=config, authn_id=authn_id, description=description
            )
            view = self.cloudauthz_serializer.serialize_to_view(
                new_cloudauthz, trans=trans, **self._parse_serialization_params(kwargs, "summary")
            )
            log.debug(f"Created a new cloudauthz record for the user id `{str(trans.user.id)}` ")
            return view
        except Exception as e:
            log.exception(msg_template.format("exception while creating the new cloudauthz record"))
            raise InternalServerError(
                "An unexpected error has occurred while responding to the create request of the "
                "cloudauthz API." + unicodify(e)
            )

    @expose_api
    def delete(self, trans, encoded_authz_id, **kwargs):
        """
        * DELETE /api/cloud/authz/{encoded_authz_id}
            Deletes the CloudAuthz record with the given ``encoded_authz_id`` from database.

        :type  trans: galaxy.webapps.base.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type  encoded_authz_id:    string
        :param encoded_authz_id:    The encoded ID of the CloudAuthz record to be marked deleted.

        :rtype  JSON
        :return The cloudauthz record marked as deleted, serialized as a JSON object.
        """

        msg_template = f"Rejected user `{str(trans.user.id)}`'s request to delete cloudauthz config because of {{}}."
        try:
            authz_id = self.decode_id(encoded_authz_id)
        except MalformedId as e:
            log.debug(msg_template.format(f"cannot decode authz_id `{encoded_authz_id}`"))
            raise e

        try:
            cloudauthz = trans.app.authnz_manager.try_get_authz_config(trans.sa_session, trans.user.id, authz_id)
            trans.sa_session.delete(cloudauthz)
            trans.sa_session.flush()
            log.debug(f"Deleted a cloudauthz record with id `{authz_id}` for the user id `{str(trans.user.id)}` ")
            view = self.cloudauthz_serializer.serialize_to_view(
                cloudauthz, trans=trans, **self._parse_serialization_params(kwargs, "summary")
            )
            trans.response.status = "200"
            return view
        except Exception as e:
            log.exception(
                msg_template.format(
                    "exception while deleting the cloudauthz record with " "ID: `{}`.".format(encoded_authz_id)
                )
            )
            raise InternalServerError(
                "An unexpected error has occurred while responding to the DELETE request of the "
                "cloudauthz API." + unicodify(e)
            )

    @expose_api
    def update(self, trans, encoded_authz_id, payload, **kwargs):
        """
        PUT /api/cloud/authz/{encoded_authz_id}

        Updates the values for the cloudauthz configuration with the given ``encoded_authz_id``.

        With this API only the following attributes of a cloudauthz configuration
        can be updated: `authn_id`, `provider`, `config`, `deleted`.

        :type  trans:               galaxy.webapps.base.webapp.GalaxyWebTransaction
        :param trans:               Galaxy web transaction

        :type  encoded_authz_id:    string
        :param encoded_authz_id:    The encoded ID of the CloudAuthz record to be updated.

        :type payload:              dict
        :param payload:             A dictionary structure containing the attributes to modified with their new values.
                                    It can contain any number of the following attributes:

                                        *   provider:   the cloud-based resource provider
                                                        to which this configuration belongs to.

                                        *   authn_id:   the (encoded) ID of a third-party authentication of a user.
                                                        To have this ID, user must have logged-in to this Galaxy server
                                                        using third-party identity (e.g., Google), or has associated
                                                        their Galaxy account with a third-party OIDC-based identity.
                                                        See this page: https://galaxyproject.org/authnz/config/

                                                        Note: A user can associate a cloudauthz record with their own
                                                        authentications only. If the given authentication with authn_id
                                                        belongs to a different user, Galaxy will throw the
                                                        ItemAccessibilityException exception.

                                        *   config:     a dictionary containing all the configuration required to
                                                        request temporary credentials from the provider.
                                                        See the following page for details:
                                                        https://galaxyproject.org/authnz/

                                        *   deleted:    a boolean type marking the specified cloudauthz as (un)deleted.

        """

        msg_template = f"Rejected user `{str(trans.user.id)}`'s request to delete cloudauthz config because of {{}}."
        try:
            authz_id = self.decode_id(encoded_authz_id)
        except MalformedId as e:
            log.debug(msg_template.format(f"cannot decode authz_id `{encoded_authz_id}`"))
            raise e

        try:
            cloudauthz_to_update = trans.app.authnz_manager.try_get_authz_config(
                trans.sa_session, trans.user.id, authz_id
            )
            self.cloudauthz_deserializer.deserialize(cloudauthz_to_update, payload, trans=trans)
            self.cloudauthz_serializer.serialize_to_view(cloudauthz_to_update, view="summary")
            return self.cloudauthz_serializer.serialize_to_view(cloudauthz_to_update, view="summary")
        except MalformedId as e:
            raise e
        except Exception as e:
            log.exception(
                msg_template.format(
                    "exception while updating the cloudauthz record with " "ID: `{}`.".format(encoded_authz_id)
                )
            )
            raise InternalServerError(
                "An unexpected error has occurred while responding to the PUT request of the "
                "cloudauthz API." + unicodify(e)
            )
