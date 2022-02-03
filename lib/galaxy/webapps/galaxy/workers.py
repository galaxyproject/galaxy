import logging

log = logging.getLogger(__name__)

try:
    import uvloop  # noqa: F401
    from uvicorn.workers import UvicornWorker as Worker
except ImportError:
    log.warning("uvloop not available, falling back to pure python worker")
    from uvicorn.workers import UvicornH11Worker as Worker  # noqa: F401
