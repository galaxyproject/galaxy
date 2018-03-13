"""
Manager and serializer for cloud-based storages.
"""

from galaxy.managers import sharable

import logging
log = logging.getLogger(__name__)


class CloudStorageManager(sharable.SharableModelManager):

    def __init__(self, app, *args, **kwargs):
        super(CloudStorageManager, self).__init__(app, *args, **kwargs)

    def download(self, provider, container, obj):
        # TODO: implement the download logic.
        pass

    def upload(self, dataset, provider, container, obj):
        # TODO: implement the upload logic.
        pass
