"""
Manager and serializer for cloud-based storages.
"""

from galaxy.managers import sharable

import logging
log = logging.getLogger(__name__)


class CloudStoragesManager(sharable.SharableModelManager):

    def __init__(self, app, *args, **kwargs):
        super(CloudStoragesManager, self).__init__(app, *args, **kwargs)

    def download(self, provider, container, object):
        # TODO: implement the download logic.
        pass

    def upload(self, dataset, provider, container, object):
        # TODO: implement the upload logic.
        pass
