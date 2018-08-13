"""
API operations on defining cloud authorizations.

Through means of cloud authorization a user is able to grant a Galaxy server a secure access to his/her
cloud-based resources without sharing his/her long-lasting credentials.

User provides a provider-specific configuration, which Galaxy users to request temporary credentials
from the provider to access the user's resources.
"""

import logging

from galaxy import web
from galaxy.exceptions import (
    ActionInputError,
    InternalServerError,
    ItemAccessibilityException,
    MalformedId,
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException
)
from galaxy.managers import cloudauthzs
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class CloudAuthzController(BaseAPIController):
    """
    RESTfull controller for defining cloud authorizations.
    """

    def __init__(self, app):
        super(CloudAuthzController, self).__init__(app)
        self.cloudauthz_manager = cloudauthzs.CloudAuthzManager(app)
        self.cloudauthz_serializer = cloudauthzs.CloudAuthzsSerializer(app)

    @web.expose_api
    def index(self, trans, **kwargs):
        """
        * GET /api/cloud/authz
            Lists all the cloud authorizations user has defined.

        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :param kwargs: empty dict

        :rtype: list of dict
        :return: a list of cloud authorizations (each represented in key-value pair format) defined for the user.
        """
        rtv = []
        for cloudauthz in trans.user.cloudauthz:
            rtv.append(self.cloudauthz_serializer.serialize_to_view(
                cloudauthz, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, 'summary')))
        return rtv

    @web.expose_api
    def create(self, trans, payload, **kwargs):
        """
        * POST /api/cloud/authz/create
            Request to store the payload as a cloudauthz (cloud authorization) configuration for a user.

        :type  trans: galaxy.web.framework.webapp.GalaxyWebTransaction
        :param trans: Galaxy web transaction

        :type payload: dict
        :param payload: A dictionary structure containing the following keys:
            *   provider:   the cloud-based resource provider to which this configuration belongs to.
            *   config:     a dictionary containing all the configuration required to request temporary credentials
                            from the provider.
            *   authn_id:   the (encoded) ID of a third-party authentication of a user. To have this ID, user must
                            have logged-in to this Galaxy server using third-party identity (e.g., Google), or has
                            associated his/her Galaxy account with a third-party OIDC-based identity. See this page:
                            https://galaxyproject.org/admin/authentication/
        :param kwargs: empty dict

        :rtype: dict
        :return: a dictionary with the following kvp:
            *   status:     HTTP response code
            *   message:    A message complementary to the response code.
        """
        if not isinstance(payload, dict):
            raise ActionInputError('Invalid payload data type. The payload is expected to be a dictionary, but '
                                   'received data of type `{}`.'.format(str(type(payload))))

        missing_arguments = []
        provider = payload.get('provider', None)
        if provider is None:
            missing_arguments.append('provider')

        config = payload.get('config', None)
        if config is None:
            missing_arguments.append('config')

        authn_id = payload.get('authn_id', None)
        if authn_id is None:
            missing_arguments.append('authn_id')

        if len(missing_arguments) > 0:
            raise RequestParameterMissingException('The following required arguments are missing in the payload: '
                                                   '{}'.format(missing_arguments))

        if not isinstance(config, dict):
            raise RequestParameterInvalidException('Invalid type for the required `config` variable; expect `dict` '
                                                   'but received `{}`.'.format(type(config)))
        try:
            authn_id = self.decode_id(authn_id)
        except Exception:
            raise MalformedId('Invalid `authn_id`!')

        self.cloudauthz_manager.can_user_assume_authn(trans, authn_id)

        try:
            new_cloudauthz = self.cloudauthz_manager.create(
                user_id=trans.user.id,
                provider=provider,
                config=config,
                authn_id=authn_id
            )
            view = self.cloudauthz_serializer.serialize_to_view(new_cloudauthz, trans=trans, **self._parse_serialization_params(kwargs, 'summary'))
            log.debug('Created a new cloudauthz record for the user id `{}` '.format(str(trans.user.id)))
            trans.response.status = '200'
            return view

        except Exception as e:
            msg = 'An unexpected error has occurred while responding to the create request of the cloudauthz API.' + str(e)
            log.exception(msg)
            raise InternalServerError(msg)
