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
    parser.add_argument('-p',
                        '--provider',
                        type=str,
                        help="Provider",
                        required=True)

    parser.add_argument('-c',
                        '--credentials',
                        type=str,
                        help="Credentials required to authorize access",
                        required=True)

    parser.add_argument('-b',
                        '--bucket',
                        type=str,
                        help="The cloud-based storage bucket in which data should be written",
                        required=True)

    parser.add_argument('-o',
                        '--object_label',
                        type=str,
                        help="The label of the object created on the cloud-based storage for "
                             "the data to be persisted",
                        required=True)

    parser.add_argument('-f',
                        '--filename',
                        type=str,
                        help="The (absolute) filename of the data to be persisted on the "
                             "cloud-based storage",
                        required=True)

    parser.add_argument('-w',
                        '--overwrite_existing',
                        type=str,
                        help="Sets if an object with the given `object_label` exists, this tool "
                             "should overwrite it (true) or append a time stamp to avoid "
                             "overwriting (false)",
                        required=True)

    args = parser.parse_args(sys.argv[1:])
    download(args.provider, args.credentials, args.bucket, args.object_label, args.filename, args.overwrite_existing)

if __name__ == "__main__":
    sys.exit(__main__())