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
from galaxy.managers import deletable
from galaxy.managers import sharable

log = logging.getLogger(__name__)


class CloudAuthzManager(sharable.SharableModelManager, deletable.PurgableManagerMixin):

    model_class = model.CloudAuthz
    foreign_key_name = 'cloudauthz'

    def __init__(self, app, *args, **kwargs):
        super(CloudAuthzManager, self).__init__(app, *args, **kwargs)


class CloudAuthzsSerializer(base.ModelSerializer, deletable.PurgableSerializerMixin):
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
            'create_time',
            'deleted'
        ])

    def add_serializers(self):
        super(CloudAuthzsSerializer, self).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        # Arguments of the following lambda functions:
        # i  : an instance of galaxy.model.CloudAuthz.
        # k  : serialized dictionary key (e.g., 'model_class', 'provider').
        # **c: a dictionary containing 'trans' and 'user' objects.
        self.serializers.update({
            'id'           : lambda i, k, **c: self.app.security.encode_id(i.id),
            'model_class'  : lambda *a, **c: 'CloudAuthz',
            'user_id'      : lambda i, k, **c: self.app.security.encode_id(i.user_id),
            'provider'     : lambda i, k, **c: str(i.provider),
            'config'       : lambda i, k, **c: str(i.config),
            'authn_id'     : lambda i, k, **c: self.app.security.encode_id(i.authn_id),
            'last_update'  : lambda i, k, **c: str(i.last_update),
            'last_activity': lambda i, k, **c: str(i.last_activity),
            'create_time'  : lambda i, k, **c: str(i.create_time),
            'deleted'      : lambda i, k, **c: str(i.deleted)
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
