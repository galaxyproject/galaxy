"""

"""

import argparse
import sys

try:
    from cloudbridge.cloud.factory import CloudProviderFactory, ProviderList
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)


def configure_provider(provider, credentials):
    pass

def download(history_id, provider, bucket, credentials, dataset_ids=None, overwrite_existing=False):
    if CloudProviderFactory is None:
        raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)
    connection = configure_provider(provider, credentials)

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