Application Server
========================================

Overview
----------------------------

It is possible to run the Galaxy server in many different ways, including under different web application frameworks, or
as a standalone server with no web stack. For most of its modern life, prior to the 18.01 release, Galaxy used the
`Python Paste`_ web stack, and ran in a single process.

Beginning with Galaxy release 18.01, the default application server for new installations of Galaxy is `uWSGI`_, which
has numerous benefits:

- Written in C and designed to be high performance.
- Internal support for serving static content.
- Supports WebSockets, which allows for support of Galaxy Interactive Environments out of the box, removing the
  dependency on Node.js.
- ...

In addition, uWSGI has been the recommended application server for production Galaxy servers for many years, but was not
previously provided with Galaxy.

What server am I running?
----------------------------

**Galaxy releases older than 18.01**

- If you start your server with the provided ``run.sh`` script, it is using Paste.
- 

Unless it has been manually configured to run under uWSGI, your server is using Paste.

**Galaxy releases 18.01 and newer**

If you upgraded from 

In any case, ``pgrep(1)`` or ``ps(1)`` should provide the answer, for example:

```sh-session
galaxy@server$ pgrep -af -u $EUID galaxy
16232 uwsgi --ini-paste config/galaxy.ini
16233 uwsgi --ini-paste config/galaxy.ini
17406 /srv/galaxy/venv/bin/python2.7 /srv/galaxy/venv/bin/uwsgi --yaml config/galaxy.yml
17419 /srv/galaxy/venv/bin/python2.7 /srv/galaxy/venv/bin/uwsgi --yaml config/galaxy.yml
17172 python ./scripts/paster.py serve config/galaxy.ini
```

The first 4 processes listed are uWSGI



If you are upgrading to Galaxy 18.01
from an older release, still have your ``galaxy.ini`` file in place, and have not manually switched to another stack
(such as uWSGI), Galaxy will continue to run under Paste.

.. _Python Paste: http://paste.readthedocs.io/
.. _uWSGI: https://uwsgi-docs.readthedocs.io/
