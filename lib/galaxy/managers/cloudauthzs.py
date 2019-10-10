"""
Manager and serializer for cloud authorizations (cloudauthzs).
"""

import logging

from galaxy import model
from galaxy.managers import base
from galaxy.managers import deletable
from galaxy.managers import sharable

log = logging.getLogger(__name__)


class CloudAuthzManager(sharable.SharableModelManager):

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
            'last_activity'
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
            'last_activity': lambda i, k, **c: str(i.last_activity)
        })
