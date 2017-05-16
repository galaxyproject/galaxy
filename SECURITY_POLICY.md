# Security

[Generic copy indicating how much Galaxy project cares about security]

## Reporting Security Issues

If you believe you have discovered a security issue, please email security@galaxyproject.org We ask that you not disclose the issues on the public issue tracker. [Should we commit to an ACK response within N hours? Would be nice from a vuln reporting perspective]

Security issues which affect a pre-release version of Galaxy (i.e. the dev branch in GitHub) do not need to go through this process, you may open issues and PRs publicly.

[Is there a pubkey it should be encrypted against?]

## Supported versions

The following branches or releases receive security support:

- Development on the `dev` branch, hosted on GitHub, which will become the next release of Galaxy
- Releases within the past 12 months.
  - E.g. 16.04 will receive support until 2017-04. As the month changes to 2017-05 it will become unsupported.
- [LTS Releases?]

Older versions of Galaxy may be affected by security issues, but we do not investigate that, nor will we issue patches or new releases of unsupported versions.

## Issue Severity

Galaxy takes a very conservative stance on issue severity as individual Galaxies often install tools and make customizations that might increase their risk in the face of otherwise less-serious vulnerabilities. As a result, issues that would be considered less-severe issues in other projects are treated as relatively higher risk.

### Issue Classification

Severity | Examples
--- | ---
High | RCE, SQL Injection, Sensitive Data Exposure, *Any issue allowing user impersonation*
Medium | XSS, CSRF [Should this be merged into high? Per @jmchilton's comments out-of-band, this seems plausible. Just remove medium class entirely?]
Low | Unvalidated redirects/forwards, Issues due to uncommon configuration options 

## Notification of Vulnerabilities

For high severity issues, we will notify a list of Galaxy instance administrators with:

- a description of the issue
- the precise steps to remedy the issue
- the set of patch(es), if any, that need to be applied to their instance
 
and embargo the issue for three (3) days. For medium and low severity issues, or high severity issues after the embargo, we will:

- Patch the oldest release within the 12 month support window, and merge that fix forward.
  - Updates will be available on the `release_XX.YY` branches.
- Create new point release tags for each release branch [??? I've never understood point release tags in Galaxy]
- Post a notice to the galaxy-dev mailing list with:  [ER: Should be galaxy-announce?]
  - The issue description
  - List of affected/patched versions 
  - Steps to update / remedy

If an issue is deemed to be time-sensitive – e.g. due to active and ongoing exploits in the wild – the embargo may be shortened considerably.

If we believe that the reported issue affects other Galaxy Project components or projects outside of the Galaxy ecosystem, we may discuss the issue with those projects and coordinate disclosure and resolution with them.

## Advance Notification

[Ok, stopping writing for now since I need to do my real job. But someone should rewrite (or heck, copy-paste + quote the django docs) on https://docs.djangoproject.com/en/dev/internals/security/#who-receives-advance-notification I rather like their section / explanation and it's probably better than I could do.]