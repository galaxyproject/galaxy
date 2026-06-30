"""Helpers for botocore S3 flexible-checksum configuration.

botocore >= 1.36 enables flexible checksums by default
(``request_checksum_calculation = "when_supported"``), adding an
``x-amz-sdk-checksum-algorithm`` header and a CRC32 checksum to every upload.
Many S3-compatible providers (Google Cloud Storage, MinIO, Cloudflare R2, Ceph,
...) don't support these AWS-specific checksum headers, so their SigV4
computation diverges from botocore's and uploads fail with ``SignatureDoesNotMatch``.

To keep those backends working out of the box, we default
``request_checksum_calculation`` to ``"when_required"`` whenever the endpoint is
not clearly AWS, while leaving real AWS on botocore's stronger default.
"""

from typing import (
    Literal,
    Optional,
    TypedDict,
)
from urllib.parse import urlparse

ChecksumSetting = Literal["when_supported", "when_required"]
WHEN_REQUIRED: ChecksumSetting = "when_required"


class S3ChecksumConfigKwargs(TypedDict, total=False):
    """botocore ``Config`` kwargs subset for S3 flexible-checksum behavior."""

    request_checksum_calculation: ChecksumSetting


def is_aws_s3_endpoint(endpoint_url: Optional[str]) -> bool:
    """Return True if the endpoint clearly targets AWS S3.

    An empty/None endpoint uses botocore's default AWS endpoint, and any host
    at or under ``amazonaws.com`` is AWS. Everything else is treated as a
    non-AWS, S3-compatible provider.
    """
    if not endpoint_url:
        return True
    host = (urlparse(endpoint_url).hostname or "").lower()
    return host == "amazonaws.com" or host.endswith(".amazonaws.com")


def s3_checksum_config_kwargs(endpoint_url: Optional[str]) -> S3ChecksumConfigKwargs:
    """botocore ``Config`` kwargs for S3 flexible-checksum behavior.

    Defaults ``request_checksum_calculation`` to ``"when_required"`` for non-AWS
    endpoints so S3-compatible providers accept uploads, while leaving real AWS
    on botocore's stronger default.
    """
    kwargs: S3ChecksumConfigKwargs = {}
    if not is_aws_s3_endpoint(endpoint_url):
        kwargs["request_checksum_calculation"] = WHEN_REQUIRED
    return kwargs
