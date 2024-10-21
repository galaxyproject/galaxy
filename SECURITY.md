# Security

The Galaxy project is strongly committed to security and responsible disclosure. We have adopted and published a set of policies specifying how we will act in response to reported security issues, in order to ensure timely updates are made available to all affected parties.

## Reporting Security Issues

If you believe you have discovered a security issue, please email [galaxy-committers@lists.galaxyproject.org](galaxy-committers@lists.galaxyproject.org). Please use `[SECURITY]` in the email title. Alternatively you can report a security vulnerability using GitHub [private reporting](https://github.com/galaxyproject/galaxy/security/advisories/new). In either case one of the maintainers will acknowledge your report within 2 US business days.

We ask that you not disclose the issues publicly. We will provide you credit for the discovery when publicly disclosing the issue.

Security issues which *only* affect a pre-release version of Galaxy (i.e. the `dev` branch in GitHub) do not need to go through this process, so you may open issues and pull requests publicly.

## Supported versions

The following branches or releases receive security support:

- Development on the `dev` branch, hosted on GitHub, which will become the next release of Galaxy
- Releases within the past 12 months.
  - E.g. 24.0 will receive support for a full year, at which point 25.0 will be available.

For unsupported branches:

- Older versions of Galaxy may be affected by security issues.
- Security patches *may* apply
- The security team does not commit to investigating issues that pertain to unsupported releases.
- The security team does not commit to issuing patches or new releases of unsupported versions.

## Issue Severity

Galaxy takes a very conservative stance on issue severity as individual Galaxy instances often install tools and make customizations that might increase their risk in the face of otherwise less-serious vulnerabilities. As a result, issues that would be considered less-severe in other projects may be treated as higher risk here.

### Issue Classification

Severity     | Examples
------------ | ---------
High         | Remote code execution (RCE), SQL Injection, Cross-site scripting (XSS), and *any issue allowing user impersonation*.
Medium / Low | Unvalidated redirects/forwards, Issues due to uncommon configuration options.

These are only examples. The security team will provide a severity classification based on its impact on the average Galaxy instance. However, Galaxy administrators should take it upon themselves to evaluate the impact for their instance(s).

## Notification of Vulnerabilities

For high severity issues, we will notify [the list of public Galaxy owners](https://lists.galaxyproject.org/lists/galaxy-public-servers.lists.galaxyproject.org/) with:

- A description of the issue
- List of supported versions that are affected
- Steps to update or patch your Galaxy

The issue will then be embargoed for three (3) days. For medium and low
severity issues, or for publicly announcing high severity issues after the
embargo, we will:

- Patch the oldest release within the 12 month support window, and merge that fix forward.
  - Updates will be available on the `release_XX.YY` branches.
- Update each release branch
- Publish a repository security advisory on GitHub containing:
  - A description of the issue
  - List of supported versions that are affected
  - Steps to update or patch your Galaxy
  - A CVE identifier (if applicable)

If an issue is deemed to be time-sensitive – e.g. due to active and ongoing exploits in the wild – the embargo may be shortened considerably.

If we believe that the reported issue affects other Galaxy Project components or projects outside of the Galaxy ecosystem, we may discuss the issue with those projects and coordinate disclosure and resolution with them.
