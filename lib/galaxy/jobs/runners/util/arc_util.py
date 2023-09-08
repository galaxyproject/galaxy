try:
    from pyarcrest.arc import ARCJob, ARCRest, ARCRest_1_1
    from pyarcrest.errors import ARCHTTPError
except ImportError:
    ARCHTTPError = None
    ARCRest_1_1 = None
    ARCJob = None


def ensure_pyarc() -> None:
    if ARCHTTPError is None:
        raise Exception("The configured functionality requires the Python package pyarcrest, but it isn't available in the Python environment.")


def get_client(cluster_url: str, token: str) -> ARCRest_1_1:
    return ARCRest.getClient(url=cluster_url, version="1.1", token=token, impls={"1.1":ARCRest_1_1})


__all__ = (
    'ensure_pyarc',
    'get_client',
    'ARCJob',
)
