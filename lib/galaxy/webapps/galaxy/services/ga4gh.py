"""Shared utilities for GA4GH service implementations."""

from urllib.parse import urlparse

from galaxy.config import GalaxyAppConfiguration
from galaxy.schema.drs import (
    Organization,
    Service,
    ServiceType,
)
from galaxy.version import VERSION


def build_service_info(
    config: GalaxyAppConfiguration,
    request_url: str,
    artifact: str,
    service_name: str,
    service_description: str,
    artifact_version: str = "1.0.0",
) -> Service:
    """Build a GA4GH Service object with Galaxy organization info.

    This utility handles the common pattern of building GA4GH service-info
    responses for services like DRS and WES.

    Args:
        config: Galaxy application configuration
        request_url: The request URL (used to extract hostname)
        artifact: The GA4GH artifact name (e.g., "drs", "wes")
        service_name: Human-readable name for the service
        service_description: Description of the service
        artifact_version: Version of the artifact specification (default "1.0.0")

    Returns:
        Service object with organization and type information
    """
    # Extract hostname from request URL
    parsed_url = urlparse(request_url)
    hostname = parsed_url.hostname or "localhost"
    scheme = parsed_url.scheme or "https"
    netloc = parsed_url.netloc

    # Build organization ID from reversed domain name
    default_organization_id = ".".join(reversed(hostname.split(".")))
    organization_id = config.ga4gh_service_id or default_organization_id
    organization_name = config.organization_name or organization_id
    organization_url = config.organization_url or f"{scheme}://{netloc}"

    # Create Organization object
    organization = Organization(
        name=organization_name,
        url=organization_url,
    )

    # Create ServiceType object
    service_type = ServiceType(
        group="org.ga4gh",
        artifact=artifact,
        version=artifact_version,
    )

    # Build extra kwargs from config
    extra_kwds = {}
    if environment := config.ga4gh_service_environment:
        extra_kwds["environment"] = environment

    # Create and return Service object
    return Service(
        id=f"{organization_id}.{artifact}",
        name=service_name,
        description=service_description,
        organization=organization,
        type=service_type,
        version=VERSION,
        **extra_kwds,
    )
