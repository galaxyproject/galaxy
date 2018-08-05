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

def load_credential(args):
    if args.credentials_file:
        with open(args.credentials_file, "r") as f:
            credentials = f.read()
        os.remove(args.credentials_file)
        return json.loads(credentials)
    else:
        if args.provider == "aws":
            return {'aws_access_key': args.ca_access_key,
                    'aws_secret_key': args.ca_secret_key}

        elif args.provider == "azure":
            return {'azure_subscription_id': args.cm_subscription_id,
                    'azure_client_id': args.cm_client_id,
                    'azure_secret': args.cm_secret,
                    'azure_tenant': args.cm_tenant}

        elif args.provider == "openstack":
            return {'os_username': args.co_username,
                    'os_password': args.co_password,
                    'os_auth_url': args.co_auth_url,
                    'os_project_name': args.co_project_name,
                    'os_project_domain_name': args.co_project_domain_name,
                    'os_user_domain_name': args.co_user_domain_name}

def download(provider, credentials, bucket, object_label, filename, overwrite_existing):
    if not os.path.exists(filename):
        raise Exception("The file `{}` does not exist.".format(filename))
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

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--provider', type=str, required=True, help="Provider")

    parser.add_argument('-b', '--bucket', type=str, required=True,
                        help="The cloud-based storage bucket in which data should be written.")

    parser.add_argument('-o', '--object_label', type=str, required=True,
                        help="The label of the object created on the cloud-based storage for "
                             "the data to be persisted.")

    parser.add_argument('-f', '--filename', type=str, required=True,
                        help="The (absolute) filename of the data to be persisted on the "
                             "cloud-based storage.")

    parser.add_argument('-w', '--overwrite_existing', type=str, required=True,
                        help="Sets if an object with the given `object_label` exists, this tool "
                             "should overwrite it (true) or append a time stamp to avoid "
                             "overwriting (false).")

    parser.add_argument('-c', '--credentials_file', type=str, required=False,
                        help="[Optional] A file that contains a JSON object containing user credentials "
                             "required to authorize access to the cloud-based storage provider."
                             "Use either this file, or pass the credentials using provider-specific args.")

    parser.add_argument('--ca_access_key', type=str, required=False, help="AWS Credentials: Access Key" )
    parser.add_argument('--ca_secret_key', type=str, required=False, help="AWS Credentials: Secret Key")

    parser.add_argument('--cm_subscription_id', type=str, required=False, help="Azure Credentials: Subscription ID")
    parser.add_argument('--cm_client_id', type=str, required=False, help="Azure Credentials: Client ID")
    parser.add_argument('--cm_secret', type=str, required=False, help="Azure Credentials: Secret")
    parser.add_argument('--cm_tenant', type=str, required=False, help="Azure Credentials: Tenant")

    parser.add_argument('--co_username', type=str, required=False, help="OpenStack Credentials: Username")
    parser.add_argument('--co_password', type=str, required=False, help="OpenStack Credentials: Password")
    parser.add_argument('--co_auth_url', type=str, required=False, help="OpenStack Credentials: Auth URL")
    parser.add_argument('--co_project_name', type=str, required=False, help="OpenStack Credentials: Project Name")
    parser.add_argument('--co_project_domain_name', type=str, required=False, help="OpenStack Credentials: Project Domain Name")
    parser.add_argument('--co_user_domain_name', type=str, required=False, help="OpenStack Credentials: User Domain Name")

    return parser.parse_args(args)

def __main__():
    args = parse_args(sys.argv[1:])
    if args.provider not in ["aws", "azure", "openstack"]:
        raise Exception("Invalid Provider `{}`; see `SUPPORTED_PROVIDERS` in lib/galaxy/managers/cloud.py "
                        "for a list of supported providers.".format(args.provider))
    overwrite_existing = args.overwrite_existing.lower() == "true"
    credentials = load_credential(args)
    download(args.provider, credentials, args.bucket, args.object_label, args.filename, overwrite_existing)

if __name__ == "__main__":
    sys.exit(__main__())