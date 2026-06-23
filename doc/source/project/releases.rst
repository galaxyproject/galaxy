======================
Galaxy Release Process
======================

This document outlines the Galaxy release cycle so administrators and users know
when to expect updates and what each update includes, making it easier to plan
for upgrades and maintain their systems.  It does not cover the actual execution
of the release process, which is covered :doc:`elsewhere <../dev/create_release>`.


Major or Long Term Support (LTS) Releases
-----------------------------------------

Starting from 23.0, the first release of each year is Galaxy's annual LTS
release, for example 24.0 is the LTS for the year 2024. A LTS release is a major
version update that receives significant and thorough end-to-end testing by a
dedicated team, and will be supported and receive bugfixes until the next LTS.
As such, this release is ideally targeted for production use by local Galaxy
administrators.


Minor Releases
--------------

Throughout the year, we also ship several (usually 2-3) minor releases. These
are version updates like 24.1, 24.2.  These can also include significant
updates, new features, etc. and follow the same release-testing protocol
as with the LTS release.  These are targeted for administrators who want to stay
up to date with the latest features and improvements.  Usegalaxy.org deploys new
minor releases as a part of the release process.


Point Releases
--------------

Point releases (e.g. 24.1.1) are issued to address bug fixes and security
updates. These are not scheduled and are released as needed. Following the Git
release branch (i.e. ``release_24.1``) is recommended to stay up to date with
these.


Release Schedule
----------------

Our release schedule is as follows:

- LTS Release: Annually, in the first quarter.
- Minor Releases: usually 2-3 times a year, generally in the early summer and fall.
- Point Releases: As needed.

Please note that the release dates can vary based on the development process and
testing results.

The usegalaxy.* public servers will be updated to the latest release within 90
business days of the release date.


Release Notes
-------------

For every release, we provide release notes that detail:

- Exciting new features
- General enhancements
- Bug fixes
- Datatype, Visualization, and Tool updates
- Administration Notes including configuration changes and migration guides if
  applicable

Please refer to the :doc:`release notes <../releases/index>` for detailed
information about each release.
