from .custos_authnz import KEYCLOAK_BACKENDS
from .psa_authnz import BACKENDS_NAME


def provider_name_to_backend(provider):
    if provider.lower() in KEYCLOAK_BACKENDS:
        return provider.lower()
    for k, v in BACKENDS_NAME.items():
        if k.lower() == provider:
            return v
    return None
