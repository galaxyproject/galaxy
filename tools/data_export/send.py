"""
This tool implements the logic of sending data
from Galaxy to a cloud-based storage.

This tool depends on the CloudManager for configuring
a connection to a cloud-based resource provider. Also,
it leverages Cloudbridge (github.com/CloudVE/cloudbridge)
to send a dataset to a cloud-based storage.

"""

import argparse
import datetime
import json
import os
import sys
import time

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.cloud import CloudManager

try:
    from cloudbridge.factory import (
        CloudProviderFactory,
        ProviderList,
    )
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)


def load_credential(credentials_file):
    print("[1/5 {}] Reading cloud authorization.".format(datetime.datetime.now().replace(microsecond=0)))
    with open(credentials_file) as f:
        credentials = f.read()
    os.remove(credentials_file)
    return json.loads(credentials)


def send(provider, credentials, bucket, object_label, filename, overwrite_existing):
    start_time = time.time()
    if not os.path.exists(filename):
        raise Exception("The file `{}` does not exist.".format(filename))
    if CloudProviderFactory is None:
        raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

    print("[2/5 {}] Establishing a connection to {}.".format(datetime.datetime.now().replace(microsecond=0), provider))
    try:
        connection = CloudManager.configure_provider(provider, credentials)
    except Exception:
        print("Failed to establish the connection.")

    print("[3/5 {}] Accessing bucket {}.".format(datetime.datetime.now().replace(microsecond=0), bucket))
    bucket_obj = connection.storage.buckets.get(bucket)
    if bucket_obj is None:
        raise ObjectNotFound("Could not find the specified bucket `{}`.".format(bucket))
    if overwrite_existing is False and bucket_obj.objects.get(object_label) is not None:
        object_label += "_" + datetime.datetime.now().strftime("%y%m%d_%H%M%S")

    print("[4/5 {}] Creating object {}.".format(datetime.datetime.now().replace(microsecond=0), object_label))
    try:
        created_obj = bucket_obj.objects.create(object_label)
    except Exception:
        print("Failed to create the object.")

    print("[5/5 {}] Sending dataset.".format(datetime.datetime.now().replace(microsecond=0)))
    transfer_start_time = time.time()
    try:
        created_obj.upload_from_file(filename)
    except Exception:
        print("Failed to send the dataset.")

    print("Finished successfully.")
    print("Job runtime:\t{}".format(time.time() - start_time))
    print(
        "Transfer ET:\t{}\tSpeed:\t{}MB/sec".format(
            time.time() - transfer_start_time,
            round((os.path.getsize(filename) >> 20) / (time.time() - transfer_start_time), 3),
        )
    )


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--provider", type=str, required=True, help="Provider")

    parser.add_argument(
        "-b",
        "--bucket",
        type=str,
        required=True,
        help="The cloud-based storage bucket in which data should be written.",
    )

    parser.add_argument(
        "-o",
        "--object_label",
        type=str,
        required=True,
        help="The label of the object created on the cloud-based storage for " "the data to be persisted.",
    )

    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        required=True,
        help="The (absolute) filename of the data to be persisted on the " "cloud-based storage.",
    )

    parser.add_argument(
        "-w",
        "--overwrite_existing",
        type=str,
        required=True,
        help="Sets if an object with the given `object_label` exists, this tool "
        "should overwrite it (true) or append a time stamp to avoid "
        "overwriting (false).",
    )

    parser.add_argument("--credentials_file", type=str, required=True, help="Credentials file")

    return parser.parse_args(args)


def __main__():
    args = parse_args(sys.argv[1:])
    overwrite_existing = args.overwrite_existing.lower() == "true"
    credentials = load_credential(args.credentials_file)
    send(args.provider, credentials, args.bucket, args.object_label, args.filename, overwrite_existing)


if __name__ == "__main__":
    sys.exit(__main__())
