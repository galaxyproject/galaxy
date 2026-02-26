# Enabling HTTP Headers in Fetch Requests

Galaxy allows users to **fetch remote data by URL** (for example via _Upload → Paste/Fetch data_ or via APIs that retrieve external resources).
By default, Galaxy **does not forward any custom HTTP headers** when fetching URLs. This restriction is intentional and is part of Galaxy’s security model.

Starting with recent Galaxy releases, administrators can **explicitly allow a controlled set of HTTP headers** to be sent with fetch requests, based on the target URL. This enables integrations with authenticated services (e.g. APIs requiring `Authorization` headers) while maintaining strict security boundaries.

This document explains **how to safely enable HTTP headers for fetch requests**, how the allow‑list mechanism works, and how to configure it.

## Why Header Allow‑Listing Is Required

Allowing arbitrary headers in server‑side HTTP requests is dangerous. Without restrictions, users could:

- Access internal services (SSRF attacks)
- Exfiltrate credentials via forwarded headers
- Abuse Galaxy as a proxy to privileged networks

To prevent this, Galaxy implements **explicit header allow‑listing with URL pattern matching**:

- **No headers are allowed by default**
- Each allowed header must be explicitly configured
- Headers are only sent to URLs that match defined patterns
- Sensitive headers can be stored securely using Galaxy’s Vault

## Configuration Overview

Header forwarding for fetch requests is controlled via a dedicated configuration file:

```yaml
galaxy:
  url_headers_config_file: url_headers_conf.yml
```

This file defines:

- Which **HTTP headers** are allowed
- For which **URL patterns** they may be sent
- Whether headers are **sensitive** (stored encrypted in the Vault)

If this configuration file is **not set or empty**, **no headers will ever be forwarded**.

## url_headers_conf.yml Format

The configuration file is a YAML list of rules. Each rule applies to one or more URL patterns.

### Basic Structure

```yaml
- url_pattern: "https://api.example.org/.*"
  headers:
    - name: Authorization
      sensitive: true
    - name: X-API-Key
      sensitive: true
```

### Fields

| Field                 | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `url_pattern`         | A regular expression matched against the full URL        |
| `headers`             | List of allowed HTTP headers for matching URLs           |
| `headers[].name`      | Exact HTTP header name (case‑insensitive)                |
| `headers[].sensitive` | Whether the header value is stored securely in the Vault |

## Sensitive vs Non‑Sensitive Headers

### Sensitive Headers

Sensitive headers (for example `Authorization`, `X-API-Key`, `Cookie`) are:

- **Encrypted and stored in the Galaxy Vault**
- Never logged or exposed in plaintext
- Managed through Galaxy’s secure secrets infrastructure

Example:

```yaml
- url_pattern: "https://protected.example.com/.*"
  headers:
    - name: Authorization
      sensitive: true
```

### Non‑Sensitive Headers

Non‑sensitive headers may be stored in plain configuration and are typically used for:

- Feature flags
- API versioning
- Public metadata headers

Example:

```yaml
- url_pattern: "https://public.example.com/.*"
  headers:
    - name: X-Client-Version
      sensitive: false
```

## Multiple Rules and URL Matching

Multiple rules may be defined. The first rule whose `url_pattern` matches the request URL is applied.

```yaml
- url_pattern: "https://api.github.com/.*"
  headers:
    - name: Authorization
      sensitive: true

- url_pattern: "https://raw.githubusercontent.com/.*"
  headers:
    - name: X-Client-Version
      sensitive: false
```

```{note}
Rules are evaluated in order. Be careful with overly broad patterns such as `.*`.
```

## Using Headers in Practice

Once configured, users (or tools) may provide header values when performing fetch operations. Galaxy will:

1. Validate the target URL against the allow‑list
2. Filter headers to the allowed set
3. Securely inject sensitive headers at request time

Headers not explicitly allowed **will be silently dropped**.

## Security Best Practices

```{warning}
Only allow headers and URL patterns that are strictly necessary.
```

Recommended practices:

- Prefer **narrow URL patterns** over wildcards
- Mark authentication headers as `sensitive: true`
- Avoid allowing `Cookie` headers unless absolutely required
- Never allow headers for internal or private network ranges

## Troubleshooting

If headers are not being forwarded as expected:

1. Verify `url_headers_config_file` is configured in `galaxy.yml`
2. Confirm the URL matches the configured `url_pattern`
3. Check that the header name matches exactly
4. Ensure Galaxy has access to the configured Vault
