"""
Manager and serializer for cloud authorizations (cloudauthzs).
"""

import logging

from galaxy import model
from galaxy.managers import sharable
from galaxy.managers import deletable

og = logging.getLogger(__name__)


class CloudAuthzManager(sharable.SharableModelManager):

    model_class = model.CloudAuthz
    foreign_key_name = 'cloudauthz'

    def __init__(self, app, *args, **kwargs):
        super(CloudAuthzManager, self).__init__(app, *args, **kwargs)
