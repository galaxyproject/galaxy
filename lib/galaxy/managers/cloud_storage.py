"""
Manager and serializer for cloud-based storages.
"""

import logging
import os
import random
import string
from cgi import FieldStorage

from galaxy.managers import sharable
from galaxy.util import Params

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

    def download(self, trans, history_id, provider, container, obj, credentials):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        aws_config = {'aws_access_key': credentials.get('access_key'),
                      'aws_secret_key': credentials.get('secret_key')}
        connection = CloudProviderFactory().create_provider(ProviderList.AWS, aws_config)
        try:
            container_obj = connection.object_store.get(container)
            if container_obj is None:
                return "400", "The container `{}` not found.".format(container)
        except Exception:
            msg = "Could not get the container `{}`".format(container)
            log.exception(msg)
            return "400", msg

        key = container_obj.get(obj)
        staging_file_name = os.path.abspath(os.path.join(
            trans.app.config.new_file_path,
            "cd_" + ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(11))))
        staging_file = open(staging_file_name, "w+")
        key.save_content(staging_file)

        with open(staging_file_name, "r") as f:
            content = f.read()
            headers = {'content-disposition': 'form-data; name="{}"; filename="{}"'.format('files_0|file_data', obj), }

            input_file = FieldStorage(headers=headers)
            input_file.file = input_file.make_file()
            input_file.file.write(content)

            inputs = {
                'dbkey': '?',
                'file_type': 'auto',
                'files_0|type': 'upload_dataset',
                'files_0|space_to_tab': None,
                'files_0|to_posix_lines': 'Yes',
                'files_0|file_data': input_file,
            }

            params = Params(inputs, sanitize=False)
            incoming = params.__dict__
            upload_tool = trans.app.toolbox.get_tool('upload1')
            history = trans.sa_session.query(trans.app.model.History).get(history_id)
            output = upload_tool.handle_input(trans, incoming, history=history)

            hids = {}
            job_errors = output.get('job_errors', [])
            if job_errors:
                raise ValueError('Cannot upload a dataset.')
            else:
                hids.update({staging_file: output['out_data'][0][1].hid})
        return "200", 'The dataset is downloaded successfully.'

    def upload(self, dataset, provider, container, obj):
        # TODO: implement the upload logic.
        pass
