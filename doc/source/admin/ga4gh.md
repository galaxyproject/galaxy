---
myst:
    substitutions:
        GA4GH_DRS: GA4GH Data Repository Service (DRS)
        GA4GH_WES: GA4GH Workflow Execution Service (WES)
---

# GA4GH API Support

Galaxy consumes many of the APIs from the [GA4GH standards](https://www.ga4gh.org/). But a
Galaxy server acts as an implementor of two of these standards currently.

## Overview

The GA4GH standards provide standardized APIs for accessing and executing workflows and datasets across different bioinformatics platforms. Galaxy's implementation allows external tools and services to:

- **DRS (Data Repository Service)**: Access Galaxy datasets via standardized data retrieval APIs
- **WES (Workflow Execution Service)**: Submit and monitor Galaxy workflow executions via standardized workflow APIs

## DRS - Data Repository Service

The {{ GA4GH_DRS }} enables standardized access to datasets stored in Galaxy.

For detailed API specifications, see the [GA4GH DRS specification](https://ga4gh.github.io/data-repository-service/).

### Configuration

DRS service information is configured via the following Galaxy settings in `galaxy.yml`:

```yaml
galaxy:
  # Organization name shown in DRS service-info responses
  organization_name: "My Organization"

  # Organization website URL shown in DRS service-info responses
  organization_url: "https://example.com"

  # GA4GH service ID (reverse domain format)
  # If not set, defaults to reversed hostname (e.g., com.example for example.com)
  ga4gh_service_id: "org.example.myservice"

  # Environment tag for service (e.g., "test", "staging", "production")
  ga4gh_service_environment: "production"
```

### Verifying DRS Configuration

To verify DRS is properly configured, query the service-info endpoint:

```bash
curl -s http://localhost:8080/ga4gh/drs/v1/service-info | jq .
```

You should see output like:

```json
{
  "id": "org.example.drs",
  "name": "Galaxy DRS API",
  "description": "Serves Galaxy datasets according to the GA4GH DRS specification",
  "organization": {
    "name": "My Organization",
    "url": "https://example.com"
  },
  "type": {
    "group": "org.ga4gh",
    "artifact": "drs",
    "version": "1.2.0"
  },
  "version": "26.0",
  "environment": "production"
}
```

Verify that:
- `organization.name` and `organization.url` match your configured values
- `environment` is set appropriately for your deployment
- `id` reflects your `ga4gh_service_id` setting (or sensible defaults if not configured)

## WES - Workflow Execution Service

The {{ GA4GH_WES }} enables external systems to submit and monitor Galaxy workflow executions.

For detailed API specifications, see the [GA4GH WES specification](https://ga4gh.github.io/workflow-execution-service-schemas/).

### Workflow Types

WES supports two Galaxy workflow formats:

- **gx_workflow_ga**: Native Galaxy XML/YAML workflow format
- **gx_workflow_format2**: Galaxy's CWL-compatible workflow format

### Configuration

WES service information is configured via the same Galaxy settings as DRS in `galaxy.yml`:

```yaml
galaxy:
  # Organization name shown in WES service-info responses
  organization_name: "My Organization"

  # Organization website URL shown in WES service-info responses
  organization_url: "https://example.com"

  # GA4GH service ID (reverse domain format)
  # If not set, defaults to reversed hostname
  ga4gh_service_id: "org.example.myservice"

  # Environment tag for service (e.g., "test", "staging", "production")
  ga4gh_service_environment: "production"
```

### Verifying WES Configuration

To verify WES is properly configured, query the service-info endpoint:

```bash
curl -s http://localhost:8080/ga4gh/wes/v1/service-info | jq .
```

You should see output like:

```json
{
  "id": "org.example.wes",
  "name": "Galaxy WES API",
  "description": "Executes Galaxy workflows according to the GA4GH WES specification",
  "organization": {
    "name": "My Organization",
    "url": "https://example.com"
  },
  "type": {
    "group": "org.ga4gh",
    "artifact": "wes",
    "version": "1.0.0"
  },
  "version": "26.0",
  "environment": "production"
}
```

Verify that:
- `organization.name` and `organization.url` match your configured values
- `environment` is set appropriately for your deployment
- `id` reflects your `ga4gh_service_id` setting (or sensible defaults if not configured)

## Configuration Reference

All GA4GH configuration is optional and falls back to sensible defaults based on your Galaxy deployment.

### Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `organization_name` | Reversed hostname | Organization name in service responses |
| `organization_url` | Scheme + hostname from request | Organization website URL |
| `ga4gh_service_id` | Reversed hostname | Service ID in reverse domain format (e.g., `org.example`) |
| `ga4gh_service_environment` | (none) | Environment classifier (e.g., "test", "staging", "production") |

### Complete Configuration Example

```yaml
# galaxy.yml - Complete GA4GH configuration
galaxy:
  # For DRS and WES service-info responses
  organization_name: "Example Bioinformatics Institute"
  organization_url: "https://example.com"

  # Service identifier (reverse domain format)
  ga4gh_service_id: "com.example.galaxy"

  # Environment classifier
  ga4gh_service_environment: "production"
```

### Default Behavior

If GA4GH settings are not explicitly configured:

- `organization_name` and `organization_url` are derived from the request URL
- `ga4gh_service_id` is auto-generated by reversing the hostname
  - For `galaxy.example.com`, this becomes `com.example.galaxy`
- `ga4gh_service_environment` is omitted from responses

## Related Documentation

- [Galaxy Workflow Guide](../learn/workflow.rst)
- [API Authentication](./authentication.md)
- [GA4GH Organization](https://www.ga4gh.org/)
