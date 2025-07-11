from .custos_authnz import KEYCLOAK_BACKENDS
from .psa_authnz import BACKENDS_NAME


def provider_name_to_backend(provider):
    if provider.lower() in KEYCLOAK_BACKENDS:
        return provider.lower()
    for k, v in BACKENDS_NAME.items():
        if k.lower() == provider:
            return v
    return None


def debug_access_token_data(access_token, social, **kwargs):
    """
    Debug auth pipeline step to add decoded access token data
    to extra_data field. Should only be used for testing,
    but needs to be at an importable path to use in the auth pipeline
    """
    social.set_extra_data({"access_token_decoded": access_token})
