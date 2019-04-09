"""
Manager and (de)serializer for cloud authorizations (cloudauthzs).
"""

import logging

from galaxy import model
from galaxy.exceptions import (
    InternalServerError,
    MalformedId
)
from galaxy.managers import base
from galaxy.managers import sharable

log = logging.getLogger(__name__)


class CloudAuthzManager(sharable.SharableModelManager):

    model_class = model.CloudAuthz
    foreign_key_name = 'cloudauthz'

    def __init__(self, app, *args, **kwargs):
        super(CloudAuthzManager, self).__init__(app, *args, **kwargs)


class CloudAuthzsSerializer(base.ModelSerializer):
    """
    Interface/service object for serializing cloud authorizations (cloudauthzs) into dictionaries.
    """
    model_manager_class = CloudAuthzManager

    def __init__(self, app, **kwargs):
        super(CloudAuthzsSerializer, self).__init__(app, **kwargs)
        self.cloudauthzs_manager = self.manager

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'model_class',
            'user_id',
            'provider',
            'config',
            'authn_id',
            'last_update',
            'last_activity',
            'create_time'
        ])

    def add_serializers(self):
        super(CloudAuthzsSerializer, self).add_serializers()

        # Arguments of the following lambda functions:
        # i  : an instance of galaxy.model.CloudAuthz.
        # k  : serialized dictionary key (e.g., 'model_class', 'provider').
        # **c: a dictionary containing 'trans' and 'user' objects.
        self.serializers.update({
            'id'           : lambda i, k, **c: self.app.security.encode_id(i.id),
            'model_class'  : lambda *a, **c: 'CloudAuthz',
            'user_id'      : lambda i, k, **c: self.app.security.encode_id(i.user_id),
            'provider'     : lambda i, k, **c: str(i.provider),
            'config'       : lambda i, k, **c: i.config,
            'authn_id'     : lambda i, k, **c: self.app.security.encode_id(i.authn_id),
            'last_update'  : lambda i, k, **c: str(i.last_update),
            'last_activity': lambda i, k, **c: str(i.last_activity),
            'create_time'  : lambda i, k, **c: str(i.create_time)
        })


class CloudAuthzsDeserializer(base.ModelDeserializer):
    """
    Service object for validating and deserializing dictionaries that
    update/alter cloudauthz configurations.
    """
    model_manager_class = CloudAuthzManager

    def add_deserializers(self):
        super(CloudAuthzsDeserializer, self).add_deserializers()
        self.deserializers.update({
            'authn_id': self.deserialize_and_validate_authn_id,
            'provider': self.default_deserializer,
            'config': self.default_deserializer,
            'deleted': self.default_deserializer
        })

    def deserialize_and_validate_authn_id(self, item, key, val, **context):
        """
        Deserializes an authentication ID (authn_id), and asserts if the
        current user can assume that authentication.

        :type  item:    galaxy.model.CloudAuthz
        :param item:    an instance of cloudauthz

        :type  key:     string
        :param key:     `authn_id` attribute of the cloudauthz object (i.e., the `item` param).

        :type  val:     string
        :param val:     the value of `authn_id` attribute of the cloudauthz object (i.e., the `item` param).

        :type  context: dict
        :param context: a dictionary object containing Galaxy `trans`.

        :rtype:         string
        :return:        decoded authentication ID.
        """

        try:
            decoded_authn_id = self.app.security.decode_id(val)
        except Exception:
            log.debug("cannot decode authz_id `" + str(val) + "`")
            raise MalformedId("Invalid `authz_id` {}!".format(val))

        trans = context.get("trans")
        if trans is None:
            log.debug("Not found expected `trans` when deserializing CloudAuthz.")
            raise InternalServerError

        try:
            trans.app.authnz_manager.can_user_assume_authn(trans, decoded_authn_id)
        except Exception as e:
            raise e

        return decoded_authn_id
