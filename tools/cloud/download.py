"""

"""

import argparse
import datetime
import json
import os
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

def load_credential(credentials_file):
    with open(credentials_file, "r") as f:
        credentials = f.read()
    os.remove(credentials_file)
    return json.loads(credentials)


def download(provider, credentials_file, bucket, object_label, filename, overwrite_existing):
    if not os.path.exists(filename):
        raise Exception("The file `{}` does not exist.".format(filename))
    credentials = load_credential(credentials_file)
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
                        '--credentials_file',
                        type=str,
                        help="A file that contains a JSON object containing user credentials "
                             "required to authorize access",
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
    overwrite_existing = args.overwrite_existing.lower() == "true"
    download(args.provider, args.credentials_file, args.bucket, args.object_label, args.filename, overwrite_existing)

if __name__ == "__main__":
    sys.exit(__main__())