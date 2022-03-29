# Migrating from uWSGI to Gunicorn and FastAPI

## Why we migrated away from uWSGI

Starting with Galaxy release 22.01 the default application webserver is [Gunicorn](https://gunicorn.org/), which replaces [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/).
We removed support for running Galaxy under uWSGI in Galaxy release 22.05.
We made this move because uWSGI support for newer Python versions has been problematic and because
we have modernized the API portion of our backend. The Galaxy web application is now an ASGI application
driven by [FastAPI](https://fastapi.tiangolo.com/) and [Starlette](https://www.starlette.io/).
This enables numerous important features that were not be possible (or were more complicated to set up)
otherwise. Importantly, [FastAPI's documentation](https://fastapi.tiangolo.com/tutorial/) is very good and
should increase developer productivity.

The main advantage for our users today is that Galaxy hosts documentation for its API as an [OpenAPI](https://www.openapis.org/)
document that is directly generated from Galaxy's source code, and so will never be out of date or differ
from the actual implementation.
Note that not all API endpoints have been modernized as of yet, this is an ongoing process.

To see the API documentation for your Galaxy server you can go to `<galaxy_url>/api/docs`.
Another immediate advantage is that parameters to all incoming API requests are validated against a [Pydantic](https://pydantic-docs.helpmanual.io/) schema.
This will lead to fewer subtle bugs and make it easier to interface with Galaxy's API.

In the future we are going to use Websockets and asynchronous programming to increase the reactivity
of the Galaxy user interface. This would not be as simple under uWSGI.

## How do I upgrade my instance to use Gunicorn

If you use `run.sh` to start Galaxy and have not set up job handling via uWSGI mules,
you do not need to do anything to start Galaxy under Gunicorn.

If you are using uWSGI mules, please read the [Scaling and Load Balancing documentation](scaling.md).
You will most likely want to set up the **Gunicorn + Webless** strategy.

If you use an upstream proxy server such as NGINX or Apache
via the uWSGI protocol, you need to replace `uwsgi_pass` and `mod_proxy_uwsgi`.
You can find detailed documentation in the [NGINX](nginx.md) and [Apache](apache.md)
documentation.

If you manage your Galaxy server via Ansible, you should continue to run Galaxy <=22.01
while we are working on updating the Ansible roles for installing Galaxy.
We will update instructions here and on the [Galaxy Training Network](https://training.galaxyproject.org/).

If you start web and job Handlers using an external process manager like
systemd or supervisor, please read the [Scaling and Load Balancing documentation](scaling.md).
In particular, you can use [gravity](https://github.com/galaxyproject/gravity) to generate supervisor configuration files
that you can either use directly or as a basis to update your existing configuration.
