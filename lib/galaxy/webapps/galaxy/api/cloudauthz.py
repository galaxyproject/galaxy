"""
API operations on defining cloud authorizations.
"""

import logging

from galaxy import web
from galaxy.managers import cloudauthzs
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class CloudAuthzController(BaseAPIController):
    """
    RESTfull controller for defining cloud authorizations.
    """

    def __init__(self, app):
        super(CloudAuthzController, self).__init__(app)
        self.cloudauthzs_manager = cloudauthzs.CloudAuthzManager(app)
        self.cloudauthzs_serializer = cloudauthzs.CloudAuthzsSerializer(app)

    @web.expose_api
    def index(self, trans, **kwargs):
        """

        :param trans:
        :param kwargs:
        :return:
        """
        rtv = []
        for cloudauthz in trans.user.cloudauthz:
            rtv.append(self.cloudauthzs_serializer.serialize_to_view(
                cloudauthz, user=trans.user, trans=trans, **self._parse_serialization_params(kwargs, 'summary')))
        return rtv

    @web.expose_api
    def create(self, trans, payload, **kwargs):
        """

        :param trans:
        :param payload:
        :param kwargs:
        :return:
        """
        if not isinstance(payload, dict):
            trans.response.status = 400
            return {'status': '400',
                    'message': 'Invalid payload data type. The payload is expected to be a dictionary, '
                               'but received data of type `{}`.'.format(str(type(payload)))}

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
            trans.response.status = 400
            return {'status': '400',
                    'message': 'The following required arguments are missing in the payload: {}'.format(missing_arguments)}

        try:
            new_cloudauthz = self.cloudauthzs_manager.create(
                user_id=trans.user.id,
                provider=provider,
                config=config,
                authn_id=authn_id
            )
            view = self.cloudauthzs_serializer.serialize_to_view(new_cloudauthz, trans=trans, **self._parse_serialization_params(kwargs, 'summary'))
            log.debug('Created a new cloudauthz record for the user id `{}` '.format(str(trans.user.id)))
            trans.response.status = '200'
            return view

        except Exception as e:
            log.exception('An unexpected error has occurred while responding to the create request of the cloudauthz API. ' + str(e))
            trans.response.status = '500 Internal Server Error'
