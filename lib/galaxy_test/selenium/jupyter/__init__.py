"""Examples and framework helpers for driving Galaxy with Selenium in Jupyter.

Example Notebooks
-----------------

There are a couple example notebooks in this directory that demonstrate two different
helper classes that provide a Python context for interacting with Galaxy.

``notebook_example_library.ipynb`` demonstrates using :class:`galaxy.selenium.jupyter_context.JupyterContext`,
an interface that only depends on the pip installable library ``galaxy-selenium``.
``JupyterContext`` inherits :class:`galaxy.selenium.navigates_galaxy.NavigatesGalaxy`
and :class:`galaxy.selenium.has_driver.HasDriver` and contains numerous functions to
interact with Galaxy in generic terms using Selenium.

``notebook_example_testing.ipynb`` demonstrates using :class:`galaxy_test.selenium.jupyter_context.JupyterTestContextImpl`,
an interface that extends ``JupyterContextImpl`` to additionally provide testing framework
populators (:mod:`galaxy_test.base.populators`) configured to work with the same
user as is logged in with Selenium and that provide a quick way to populate the target
Galaxy with testing fixtures.

The first example notebook is good for prototyping stand-alone applications that drive
Galaxy, the second example notebook is setup to mirror the environment available to Selenium
test cases that ship with Galaxy (e.g. :class:`galaxy_test.selenium.framework:SeleniumTestCase`)
and can be used for interactively developing Selenium tests for Galaxy. Additionally, it shows how can ActionChains
could be accessed within Jupyter notebook.

These notebooks start with a cell that simply defines a ``config`` variable in the Python
environment on a cell that is marked with metadata indicated it is "parameters". This
isn't required at all to use the notebook iteratively, but it does provide a nice hook
for executing the notebook in a parameterized way using papermill_ after its creation.

The second cell in both of these notebooks setup the Galaxy interaction context - either
a :class:`galaxy.selenium.jupyter_context.JupyterContextImpl` or
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

.. note:: Using Papermill

    ::

        $ . venv/bin/activate  # first two commands only needed first time
        $ pip install papermill
        $ papermill galaxy_test/selenium/jupyter/notebook_example_library.ipynb  galaxy_test/selenium/jupyter/notebook_example_library_output.ipynb -y "
        config: {local_galaxy_url: 'http://localhost:8081/'}
        "

Developing Galaxy Test Cases Interactively with Jupyter
-------------------------------------------------------

The Setup
~~~~~~~~~

Writing Selenium tests for Galaxy often involves annotating the Galaxy DOM with
appropriate ``class`` and ``data-*`` attributes, so it is best to have webpack monitor
``client/src`` and rebuild as things changes and then disable building the client
as Galaxy starts. This can be done by executing the follow two commands in separate
terminal sessions.

::

    $ GALAXY_SKIP_CLIENT_BUILD=1 GALAXY_RUN_WITH_TEST_TOOLS=1 sh run.sh
    $ make client-watch

Copy ``lib/galaxy_test/selenium/jupyter/galaxy_selenium.yml.sample`` to
``lib/galaxy_test/selenium/jupyter/galaxy_selenium.yml`` and specify a
``login_email``, ``login_password``, ``admin_api_key`` to point at values
suitable for your local test environment.

::

    $ cp lib/galaxy_test/selenium/jupyter/galaxy_selenium.yml.sample lib/galaxy_test/selenium/jupyter/galaxy_selenium.yml
    $ vi lib/galaxy_test/selenium/jupyter/galaxy_selenium.yml

Start Jupyter for interactive development. This requires Jupyter to be
available in Galaxy's virtual environment.

::

    $ . venv/bin/activate  # first two commands only needed first time
    $ pip install jupyter
    $ make serve-selenium-notebooks

Filling out Tests
~~~~~~~~~~~~~~~~~~~~

Open (or copy and open) the notebook ``notebook_example_testing.ipynb`` and
start developing the test in the third notebook cell. This cell will land up
being the body a test case.

Use ``gx_selenium_context`` to navigate Galaxy, setup test conditions, and
verify expected behavior. Change ``navigation.yml`` to implement components and
``client/src`` to annotate the source - these changes will be picked up automatically
and you can simply re-run the notebook to redo the modified or extended test.
If Python test code needs to be changed (e.g. helper methods are added to
:class:`galaxy.selenium.navigates_galaxy.NavigatesGalaxy`), you'll need to
select "Restart & Run All" from the "Kernel" menu of Jupyter to pickup the new
changes.


Once the test is complete, copy all the cells after the initialization into a
new test case file (either in ``lib/galaxy_test/selenium`` or
``test/integration_selenium``). Some examples of pull request commits developed this
way include Galaxy's initial `workflow invocation detail tests
<https://github.com/galaxyproject/galaxy/pull/11160/commits/b6d99320d99e93f812adc0df494447525978ebfa>`__
and initial `history import and export tests <https://github.com/galaxyproject/galaxy/pull/11152/files>`__.
These commits demonstrate the basics of how to turn operations on a ``gx_selenium_context``
into a Galaxy test case, how to add UI selectors to ``navigation.yml``, how to add
functionality to ``navigates_galaxy.py`` to be shared across test cases.
The `history import and export tests <https://github.com/galaxyproject/galaxy/pull/11152/files>`__
additionally are examples of both regular Selenium test cases as well as their
integration-style variant that configures Galaxy before the test runs.

Much more information on structuring Selenium test cases generally, the difference
between tests that should be place in ``lib/galaxy_test/selenium`` versus ones
that should be placed in ``test/integration_selenium``, and information on running
Selenium test cases can all be found in :doc:`../dev/writing_tests`.

.. note::

    Test Case Attributes

    If you'd like to simplify your test by logging into Galaxy as a pre-condition,
    add ``ensure_registered = True`` on the test case class. Your test case can
    use an admin key to populate fixtures without any extra annotation but to ensure
    a user logged in with ``ensure_registered`` is an admin user simply annotate
    your test case with ``requires_admin = True``.

.. _papermill: https://papermill.readthedocs.io/en/latest/

"""
