# Writing Tests for Galaxy

[Other Sources of Documentation](#other_sources)  
[An Overview of Galaxy Tests](#overview)  
[Backend/Python Unit Tests](#python_unit)  
[Frontend/ES6 Unit Tests](#es6_unit)  
[Tool Framework Tests](#framework)  
[API Tests](#api)  
[Integration Tests](#integration)  
[Selenium Tests](#selenium)  
[Selenium Integration Tests](#selenium_integration)  
[Running Python Tests](#running_tests)

## <a name="other_sources"></a> Other Sources of Documentation

Over the last several years, the most up-to-date documentation on the
structure and running of Galaxy tests has been in the help text for
run_tests.sh script shipped with Galaxy (``./run_tests.sh --help``).
High-level information on Galaxy's CI process can be found in the
[Galaxy Code Architecture Slides](https://training.galaxyproject.org/training-material/topics/dev/tutorials/architecture/slides.html)
and the corresponding [YouTube playlist](https://bit.ly/gx-arch-vids).
Some more specifics on running and writing Galaxy client unit tests
can be found in ``client/README.md`` of the Galaxy codebase.

## <a name="overview"></a> An Overview of Galaxy Tests

Galaxy has many test suites and frameworks. A potentially overwhelming question
at first is, *where does a given test belong? What testing suite or framework
should it be added to?* The following questions may be able to help
find the right documentation for a given test one wishes to write.

***Does this test require a running server and database to execute?***

  - **No**

    If no, this test should probably be implemented as a Galaxy unit test. Unit tests generally, and Galaxy ones specifically, are especially useful
    for complex components that are well architected to be tested in isolation.
    The best unit tests are unit tests that shield a lot of their potential complexity from their
    consumers and components that do not have a lot of dependencies - especially
    on the database or a web server.

    ***Is the component under test a client (ES6) or backend (Python) component?***

      - **Client/ES6**

        These tests should be placed in ``client/src`` directly and executed
        via Jest. Checkout [Frontend/ES6 Unit Tests](#es6_unit) below for more
        information.

      - **Backend/Python**

        These tests should be placed in ``test/unit`` or doctests and
        executed via pytest. Checkout [Backend/Python Unit Tests](#python_unit) below for more
        information.

  - **Yes**

    In this case you're looking at some sort of functional test that requires
    a running Galaxy server and the Galaxy database. All of these tests are
    currently implemented in Python.

    ***Does this test require the Galaxy web interface?***

      - **No**

        Most of the time, we have found that these tests work best when
        they use the Galaxy API to drive the test. These tests
        are all Python tests executed by pytest. The testing frameworks
        provide everything you need to spin up a Galaxy instance,
        communicate with its API to invoke the component under test,
        and write expectations about the outcome of the test.
        There are three different (but very related) frameworks to do this
        and the choice between which is appropriate comes down to
        the following questions.

        ***Does this test require a special configuration of Galaxy?***

          - **No**

            ***Does this test check only functionalities of Galaxy tools?***

            - **Yes**

              In this case you do not actually need to deal with the Galaxy API
              directly and you can just create a Galaxy tool test to check that
              the required functionality does work as expected. These are called
              Galaxy tool framework tests and are located in
              ``test/functional/tools/``. Checkout
              [Tool Framework Tests](#framework) below for more information.

            - **No**
           
              In this case Galaxy API tests are likely the most
              appropriate way to implement the desired test. These tests
              are located in ``lib/galaxy_test/api``. Checkout
              [API Tests](#api) below for more information.

          - **Yes**

            Tests that require a custom Galaxy with a very specific 
            configuration are called Galaxy integration tests and are located in
            ``test/integration``.  Checkout [Integration Tests](#integration)
            below for more information.

      - **Yes**

        The tests that exercise the Galaxy user interface and require
        a functional Galaxy server use [Selenium](https://www.selenium.dev/) to drive interaction
        with the Galaxy web interface. There are two frameworks or suites
        available for building tests like this and they both provide high
        level access to the Galaxy API like the tests above. The frameworks
        also take care of starting the Galaxy server.

        The choice between these two different frameworks comes down to the
        answer to the following question.

        ***Does this test require a special configuration of Galaxy?***

          - **No**

            These tests should be placed into ``lib/galaxy_test/selenium`` 
            and implemented using the [Selenium Tests](#selenium)
            framework describe below.

          - **Yes**

            Tests that require both a very specific Galaxy configuration
            as well as the ability to drive a running Galaxy web interface
            should be placed into ``test/integration_selenium``. Checkout
            the [Selenium Integration Tests](#selenium_integration)
            information below for more information.

## <a name="python_unit"></a> Backend/Python Unit Tests

These are Python unit tests either defined inside of ``test/unit`` or
via doctests within a Python component. These should generally not require
a Galaxy instance and should quickly test just a component or a few
components of Galaxy's backend code.

### doctests to stand-alone tests?

doctests tend to be more brittle and more restrictive. I (@jmchilton)
would strongly suggest writing stand-alone unit testing files separate
from the code itself unless the tests are so clean and so isolated they
serve as high-quality documentation for the component under test.

### Slow 'Unit' Tests

There are tests in Galaxy that test integration with external sources
that do not require a full Galaxy server. While these aren't really
"unit" tests in a traditional sense, they are unit tests from a Galaxy
perspective because they do not depend on a Galaxy server.

These tests should be marked as requiring the environment variable
``GALAXY_TEST_INCLUDE_SLOW`` to run.

### Continuous Integration

The Python unit tests are run against each pull request to Galaxy using
CircleCI. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
CircleCI test definition for these tests is located in ``.circleci/config.yml``
below Galaxy's root.

## <a name="es6_unit"></a> Frontend/ES6 Unit Tests

Detailed information on writing Galaxy client tests can be found in
[client/README.md](https://github.com/galaxyproject/galaxy/blob/dev/client/README.md#client-side-unit-testing).

### Continuous Integration

The client tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/jest.yaml`` below Galaxy's root.

## <a name="framework"></a> Tool Framework Tests

A great deal of the complexity and interface exposed to Galaxy plugin 
developers comes in the form of Galaxy tool wrapper definition files.
Likewise, a lot of the legacy behavior Galaxy needs to maintain is
maintained for older tool definitions. For this reason, a lot of Galaxy's
complex internals can just be tested by simply running a tool test.
Obviously Galaxy is much more complex than this, but a surprising amount
of Galaxy's tests are simply tool tests. This suite of tools that
have their tests exercised is called the "Tool Framework Tests"
or simply "Framework Tests".

Adding a tool test is as simple as finding a related tool in the sample
tools (``test/functional/tools``) and adding a test block to that file
or adding a new tool to this directory and referencing it in the
sample tool configuration XML (``test/functional/tools/samples_tool_conf.xml``).

General information on writing Galaxy Tool Tests can be found in Planemo's
documentation - for instance in the [Test-Driven Development](https://planemo.readthedocs.io/en/latest/writing_advanced.html#test-driven-development)
section.

### Continuous Integration

The Tool framework tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is fairly stable and typically there are not
transiently failed tests unrelated to the pull request being tested. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/framework.yaml`` below Galaxy's root.

## <a name="api"></a> API Tests

These tests are located in ``lib/galaxy_test/api`` and test various aspects 
of the Galaxy API, as well as general backend aspects of Galaxy using the API.

### An Example: ``lib/galaxy_test/api/test_roles.py``

This test file shows a fairly typical API test. It demonstrates the basic
structure of a test, how to ``GET`` and ``POST`` against the API, and how to use
both typical user and admin user-only functionality.

### Common Code for Populating Fixture Data

The [``galaxy_test.base.populators``](../lib/galaxy_test.base.html#module-galaxy_test.base.populators) module contains detailed docstrings
describing the concept and implementation of "Populators" that can be used
for this purposes.

The ``test_roles.py`` example creates a ``DatasetPopulator``
object that it uses to get some common information from the configured
Galaxy server under test.

Populators are used extensively throughout API tests as well as integration
and Selenium tests to both populate data to test (histories, workflows,
collections, libraries, etc..) as well as access information from the
Galaxy server (e.g. fetch information from datasets, users, Galaxy's
configuration, etc.).

Populators and API tests in general make heavy use of the [requests
library](https://requests.readthedocs.io/en/master/) for Python.

### API Test Assertions

The ``galaxy_test.base.api_asserts`` module contains common
assertion functions used to check API request status codes, dictionary
content, and Galaxy specific error messages.

See [``galaxy_test.base.api_asserts`` documentation](../lib/galaxy_test.base.html#module-galaxy_test.base.api_asserts)
for details on each function and information on verifying Galaxy API error codes.

### Continuous Integration

The API tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is fairly stable and typically there are not
transiently failed tests unrelated to the pull request being tested. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/api.yaml`` below Galaxy's root.

## <a name="integration"></a> Integration Tests

These tests are located in ``test/integration``. These tests have access
to all the same API utilities as API tests described above, but can access
Galaxy internals and may define hooks for configuring Galaxy in certain ways 
during startup.

Galaxy integration tests in some ways are more powerful than API tests - 
they can both control Galaxy's configuration and can access Galaxy's
internals. However, this power comes at a real cost - each test case must
spin up its own Galaxy server (a relatively expensive operation) and the
tests cannot be executed against external Galaxy servers (it wouldn't make
sense to, given these custom hooks during configuration of the server).
For these reasons, we bundle up Galaxy API tests for use in deployment
testing of production setups. Therefore Galaxy API tests are generally preferred,
while integration tests should be implemented only when an API test is not
possible or practical.

Integration tests can make use of dataset populators and API assertions
as described above in the API test documentation. It is worth reviewing
that documentation before digging into integration examples.

### An Example: ``test/integration/test_quota.py``

This is a really simple example that does some testing with the Quotas
API of Galaxy. This API is off by default so it must be enabled for the
test. The top of the test file demonstrates both how to create an
integration test and how to modify Galaxy's configuration for the test.

```python
#...
from galaxy_test.driver import integration_util


class QuotaIntegrationTestCase(integration_util.IntegrationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["enable_quotas"] = True

    #...
```

Integration test cases extend the ``IntegrationTestCase`` class defined in
the ``galaxy_test.driver.integration_util`` module (located in
``lib/galaxy_test/driver/integration_uti.py`` below Galaxy's root).

The ``require_admin_user`` option above tell the test framework that the
default user configured for API interactions must be an admin user.

This example overrides Galaxy's configuration using the 
``handle_galaxy_config_kwds`` class method. This method is called before
a Galaxy server is created, and is passed the testing server's default 
configuration as the ``config`` argument to that class method. This
``config`` object is effectively the Python representation of the Galaxy
configuration file (``galaxy.yml``) used to start the Python server.
Almost anything you can do in ``galaxy.yml``, you can modify the Galaxy
server to do using the same keys. Examples of various ways integration tests
have modified this dictionary include setting up custom object stores
(e.g. ``objectstore/test_mixed_store_by.py``),
setting up non-local job runners (e.g. ``test_cli_runners.py``), setting
up custom job destinations (e.g. ``test_job_recovery.py``), and configuring 
Galaxy for tool shed operations (e.g. ``test_repository_operations.py``).

There may be cases where an integration test is used not to allow
some custom configuration of Galaxy but to access Galaxy's internals.
Integration tests have direct access to Galaxy's ``app`` object via
``self._app`` and direct access to the database as a result. An example of
such a test is ``test_workflow_refactoring.py``. This test required accessing
the way workflow steps are stored in the database and not just how they are
serialized by the API, so it tests database models directly. Generally
though, this type of usage should be avoided.

### Continuous Integration

The Integration tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/integration.yaml`` below Galaxy's root.

## <a name="selenium"></a> Selenium Tests

These are full stack tests meant to test the Galaxy UI with real
browsers and are located in ``lib/galaxy_test/selenium``.

### Jupyter + Selenium

Jupyter can leveraged to develop Selenium test cases interactively,
checkout out the [``galaxy_test.selenium.jupyter``](../lib/galaxy_test.selenium.jupyter)
for more a full discussion of this.

### Continuous Integration

The Selenium tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/selenium.yaml`` below Galaxy's root.

## <a name="selenium_integration"></a> Selenium Integration Tests

These tests are located in ``test/integration_selenium`` and simply
combine the capabilities of Selenium tests and Integration tests
(both described above) into test cases that can do both. There
are no new capabilities or gotchas of this test suite beyond
what is described above in these sections.

A quintessential example is ``test/integration_selenium/test_upload_ftp.py``.
Testing the FTP capabilities of the user interface requires both
Selenium to drive the test case and a custom Galaxy configuration
that mocks out an FTP directory and points the Galaxy server at it
with various options (``ftp_upload_dir``, ``ftp_upload_site``).

### Continuous Integration

The Selenium integration tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/selenium_integration.yaml`` below Galaxy's root.

## <a name="running_tests"></a> Running Python Tests

The best information about how to run Galaxy's Python tests can be
found in the help output of ``run_tests.sh --help``.

```eval_rst
.. include:: run_tests_help.txt
   :literal:
```
