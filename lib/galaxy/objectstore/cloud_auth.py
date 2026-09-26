"""Provider credential rules shared by the cloud object store and its templates.

A leaf module so both ``galaxy.objectstore.cloud`` and
``galaxy.objectstore.templates.models`` can read the same rules; importing the
store itself from the templates would be circular (the store reaches
``galaxy.objectstore``, which imports the templates).
"""

import logging
from typing import Any

log = logging.getLogger(__name__)

# Galaxy's <auth> option names paired with the cloudbridge provider config key
# each one sets. XML parsing, provider construction and the required-field check
# read these; the template models declare their own narrower field set.
AUTH_KEY_MAP: dict[str, tuple[tuple[str, str], ...]] = {
    "aws": (
        ("access_key", "aws_access_key"),
        ("secret_key", "aws_secret_key"),
        ("session_token", "aws_session_token"),
        ("region", "aws_region_name"),
    ),
    "azure": (
        ("subscription_id", "azure_subscription_id"),
        ("client_id", "azure_client_id"),
        ("secret", "azure_secret"),
        ("tenant", "azure_tenant"),
        ("access_token", "azure_access_token"),
        ("storage_account", "azure_storage_account"),
        ("resource_group", "azure_resource_group"),
        ("region", "azure_region_name"),
    ),
    "google": (
        ("credentials_file", "gcp_service_creds_file"),
        ("credentials_dict", "gcp_service_creds_dict"),
        ("region", "gcp_region_name"),
    ),
    "openstack": (
        ("username", "os_username"),
        ("password", "os_password"),
        ("project_name", "os_project_name"),
        ("auth_url", "os_auth_url"),
        ("region", "os_region_name"),
        ("user_domain_name", "os_user_domain_name"),
        ("project_domain_name", "os_project_domain_name"),
        ("application_credential_id", "os_application_credential_id"),
        ("application_credential_secret", "os_application_credential_secret"),
    ),
}

# Options that cannot be expressed as an XML attribute.
NON_XML_AUTH_KEYS = {"credentials_dict"}

# Only the S3-compatible provider takes <connection> options.
CONNECTION_KEY_MAP: dict[str, tuple[tuple[str, str], ...]] = {
    "aws": (
        ("endpoint_url", "s3_endpoint_url"),
        ("validate_certs", "s3_validate_certs"),
        ("signature_version", "s3_signature_version"),
    ),
}

# Name of the cloudbridge ProviderList member backing each Galaxy provider.
PROVIDER_LIST_NAMES = {"aws": "AWS", "azure": "AZURE", "google": "GCP", "openstack": "OPENSTACK"}


def validate_auth(provider: str, credentials: dict[str, Any]) -> None:
    """Raise unless the credentials carry a credential set the provider accepts.

    Every configuration path -- XML, YAML and user-defined templates -- reaches
    this, so a store that cannot authenticate is rejected before it is built.
    """
    missing = []
    if provider == "azure" and not credentials.get("access_token"):
        # Without an access token the service-principal quartet is required.
        missing = [k for k in ("subscription_id", "client_id", "secret", "tenant") if not credentials.get(k)]
    elif provider == "openstack":
        if not credentials.get("auth_url"):
            missing.append("auth_url")
        application_credential = ("application_credential_id", "application_credential_secret")
        if any(credentials.get(k) for k in application_credential):
            # Keystone needs both halves; half of one is never usable.
            missing += [k for k in application_credential if not credentials.get(k)]
        else:
            # Without an application credential, password authentication is required.
            missing += [k for k in ("username", "password", "project_name") if not credentials.get(k)]
    elif provider == "google":
        if bool(credentials.get("credentials_file")) == bool(credentials.get("credentials_dict")):
            raise ValueError("The google provider requires exactly one of credentials_file or credentials_dict.")
    if missing:
        msg = f"The following configuration required for {provider} cloud backend are missing: {missing}"
        log.error(msg)
        raise ValueError(msg)


def validate_user_defined_auth(provider: str, credentials: dict[str, Any]) -> None:
    """Validate credentials for a store a user defines from a template.

    Stricter than :func:`validate_auth`: an admin may deliberately configure an
    AWS store with no keys in object_store_conf.yml so the instance role is
    used, but a user-defined store must never fall back to Galaxy's own
    identity, so it has to carry its own keys.
    """
    validate_auth(provider, credentials)
    if provider == "aws":
        missing = [k for k in ("access_key", "secret_key") if not credentials.get(k)]
        if missing:
            raise ValueError(f"The following configuration required for aws cloud backend are missing: {missing}")
