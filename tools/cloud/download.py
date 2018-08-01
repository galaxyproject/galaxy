"""

"""

import argparse
import datetime
import sys

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.cloud import CloudManager


try:
    from cloudbridge.cloud.factory import CloudProviderFactory, ProviderList
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)


def download(provider, credentials, bucket, object_label, filename, overwrite_existing):
    if CloudProviderFactory is None:
        raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)
    connection = CloudManager.configure_provider(provider, credentials)
    bucket_obj = connection.object_store.get(bucket)
    if bucket_obj is None:
        raise ObjectNotFound("Could not find the specified bucket `{}`.".format(bucket))
    if overwrite_existing is False and bucket_obj.get(object_label) is not None:
        object_label += "-" + datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    created_obj = bucket_obj.create_object(object_label)
    created_obj.upload_from_file(filename)

def __main__():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--provider', type=str, help="Provider", required=True)
    parser.add_argument('-a', '--access', type=str, help="AWS access key", required=True)
    parser.add_argument('-s', '--secret', type=str, help="AWS secret key", required=True)
    parser.add_argument('-b', '--bucket', type=str, help="AWS S3 bucket name", required=True)
    parser.add_argument('-o', '--object', type=str, help="AWS S3 object name", required=True)
    parser.add_argument('-u', '--output', type=str, help="Downloaded file", required=True)
    args = parser.parse_args(sys.argv[1:])
    download(args)

if __name__ == "__main__":
    __main__()