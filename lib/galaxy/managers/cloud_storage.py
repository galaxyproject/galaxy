"""
Manager and serializer for cloud-based storages.
"""

import string
import random
import logging
import os
from galaxy.managers import sharable

try:
    from cloudbridge.cloud.factory import CloudProviderFactory, ProviderList
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

log = logging.getLogger(__name__)

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)


class CloudStorageManager(sharable.SharableModelManager):

    def __init__(self, app, *args, **kwargs):
        super(CloudStorageManager, self).__init__(app, *args, **kwargs)

    def download(self, trans, provider, container, obj, credentials):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        aws_config = {'aws_access_key': credentials.get('access_key'),
                      'aws_secret_key': credentials.get('secret_key')}
        connection = CloudProviderFactory().create_provider(ProviderList.AWS, aws_config)

        try:
            container_obj = connection.object_store.get(container)
            if container_obj is None:
                return 400, "The container `{}` not found.".format(container)
        except Exception:
            msg = "Could not get the container `{}`".format(container)
            log.exception(msg)
            return 400, msg

        key = container_obj.get(obj)
        staging_file_name = os.path.abspath(os.path.join(
            trans.app.config.new_file_path,
            "cd_" + ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(11))))
        staging_file = open(staging_file_name, "w+")
        key.save_content(staging_file)
        pass

    def upload(self, dataset, provider, container, obj):
        # TODO: implement the upload logic.
        pass
