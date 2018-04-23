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
    from cloudbridge.cloud.interfaces.exceptions import ProviderConnectionException
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

log = logging.getLogger(__name__)

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)

SUPPORTED_PROVIDERS = "{aws, azure}"


class CloudManager(sharable.SharableModelManager):

    def __init__(self, app, *args, **kwargs):
        super(CloudManager, self).__init__(app, *args, **kwargs)

    def _configure_provider(self, provider, credentials):
        missing_credentials = []
        if provider == 'aws':
            access = credentials.get('access_key', None)
            if access is None:
                missing_credentials.append('access_key')
            secret = credentials.get('secret_key', None)
            if secret is None:
                missing_credentials.append('secret_key')
            if len(missing_credentials) > 0:
                return "400", "The following required key(s) are missing from the provided credentials object: " \
                              "{}".format(missing_credentials), None

            config = {'aws_access_key': access,
                      'aws_secret_key': secret}
            connection = CloudProviderFactory().create_provider(ProviderList.AWS, config)
        elif provider == "azure":
            subscription = credentials.get('subscription_id', None)
            if subscription is None:
                missing_credentials.append('subscription_id')
            client = credentials.get('client_id', None)
            if client is None:
                missing_credentials.append('client_id')
            secret = credentials.get('secret', None)
            if secret is None:
                missing_credentials.append('secret')
            tenant = credentials.get('tenant', None)
            if tenant is None:
                missing_credentials.append('tenant')
            if len(missing_credentials) > 0:
                return "400", "The following required key(s) are missing from the provided credentials object: " \
                              "{}".format(missing_credentials), None

            config = {'azure_subscription_id': subscription,
                      'azure_client_id': client,
                      'azure_secret': secret,
                      'azure_tenant': tenant}
            connection = CloudProviderFactory().create_provider(ProviderList.AZURE, config)
        else:
            return "400", "Unrecognized provider '{}'; the following are the supported providers: {}.".format(
                provider, SUPPORTED_PROVIDERS), None

        try:
            if connection.authenticate():
                return "200", "", connection
        except ProviderConnectionException as e:
            return "400", "Could not authenticate to the '{}' provider. {}".format(provider, e), None

    def download(self, trans, history_id, provider, container, obj, credentials):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        status, msg, connection = self._configure_provider(provider, credentials)
        if status != "200":
            return status, msg
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

        datasets = []
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
                for d in output['out_data']:
                    datasets.append(d[1].dataset)
        os.remove(staging_file_name)
        return datasets

    def upload(self, dataset, provider, container, obj):
        raise NotImplementedError
