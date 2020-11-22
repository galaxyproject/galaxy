"""Examples and framework helpers for driving Galaxy with Selenium in Jupyter.

There are a couple example notebooks in this directory that demonstrate two different
helper classes that provide a Python context for interacting with Galaxy.

``notebook_example_library.ipynb`` demonstrates using :class:`galaxy.selenium.jupyter_context.JupyterContext`,
an interface that only depends on the pip installable library ``galaxy-selenium``.
``JupyterContext`` inherits :class:`galaxy.selenium.navigates_galaxy.NavigatesGalaxy`
and :class:`galaxy.selenium.has_driver.HasDriver` and contains numerous functions to
interact with Galaxy in generic terms using Selenium.

``notebook_example_testing.ipynb`` demonstrates using :class:`galaxy_test.selenium.jupyter_context.JupyterTestContextImpl`,
an interface that extends ``JupyterContext`` to additionally provide testing framework
populators (:mod:`galaxy_test.base.populators`) configured to work with the same
user as is logged in with Selenium and that provide a quick way to populate the target
Galaxy with testing fixtures.

The first example notebook is good for prototyping stand-alone applications that drive
Galaxy, the second example notebook is setup to mirror the environment available to Selenium
test cases that ship with Galaxy (e.g. :class:`galaxy_test.selenium.framework:SeleniumTestCase`)
and can be used for interactively developing Selenium tests for Galaxy.

These notebooks start with a cell that simply defines a ``config`` variable in the Python
environment on a cell that is marked with metadata indicated it is "parameters". This
isn't required at all to use the notebook iteratively, but it does provide a nice hook
for executing the notebook in a parameterized way using papermill_ after its creation.

The second cell in both of these notebooks setup the Galaxy interaction context - either
a :class:`galaxy.selenium.jupyter_context.JupyterContext` or
:class:`galaxy_test.selenium.jupyter_context.JupyterTestContextImpl` depending on
the notebook. These cells use a function named ``init`` to create the desired
interaction context (called ``gx_selenium_context`` in both cases).

::

    from galaxy.selenium.jupyter_context import init
    gx_selenium_context = init(config)

The optional ``config`` dictionary can be used to configure both Selenium and the Galaxy
that is targeted. If ``config`` is none and the working directory Jupyter is executing
inside of has a file named ``galaxy_selenium_context.yml`` - ``init`` will read that file
and use it as the target configuration.

Both contexts can be configured with the following dictionary keys (either from
``galaxy_selenium_context.yml`` or using papermill_).

``local_galaxy_url``
    Galaxy URL to target during execution.

``selenium_galaxy_url``
    Galaxy URL relative to the Selenium being used. This doesn't need to be set unless
    you're using a remote Selenium server (i.e one not running directly on ``localhost``).

``driver``
    If set, this should be a dictionary describing variables to send to
    :class:`galaxy.selenium.driver_factory.ConfiguredDriver` and define how to
    setup the Selenium client used. Useful keys and their defaults include -
    ``browser`` (``"auto"``), ``remote`` (``false``), ``remote_host`` (``"127.0.0.1"``),
    ``remote_port`` (``4444``), ``headless`` (``false``).

Additionally, the testing context also allows additional configuration variables used
for populating test fixtures (with populators) or by extra testing helpers (e.g.
``gx_selenium_context.test_login()``).

``admin_api_key``
    An API key to be used for API interactions that require an admin account.

``login_email``
    A test account login or email address to be used for tests that require a logged
    in user.

``login_password``
    The password to be used for the account referenced by ``login_email``.

.. note: Using Papermill

    ::

        $ . venv/bin/activate
        $ pip install papermill
        $ papermill galaxy_test/selenium/jupyter/notebook_example_library.ipynb  galaxy_test/selenium/jupyter/notebook_example_library_output.ipynb -y "
        config: {local_galaxy_url: 'http://localhost:8081/'}
        "

.. _papermill: https://papermill.readthedocs.io/en/latest/

"""
