# Writing Tests for Galaxy

```{contents} Contents
:depth: 1
:local:
```

{#other_sources}
## Other Sources of Documentation

Over the last several years, the most up-to-date documentation on the
structure and running of Galaxy tests has been in the help text for
run_tests.sh script shipped with Galaxy (``./run_tests.sh --help``).
High-level information on Galaxy's CI process can be found in the
[Galaxy Code Architecture Slides](https://training.galaxyproject.org/training-material/topics/dev/tutorials/architecture/slides.html)
and the corresponding [YouTube playlist](https://bit.ly/gx-arch-vids).
The [GTN Writing Tests Tutorial](https://training.galaxyproject.org/training-material/topics/dev/tutorials/writing_tests/tutorial.html)
provides hands-on exercises covering API tests, unit tests, and patterns for
making code testable (monkeypatching, stubs, parametrization).
Some more specifics on running and writing Galaxy client unit tests
can be found in ``client/README.md`` of the Galaxy codebase.

{#overview}
## An Overview of Galaxy Tests

### Quick Reference

| Test Type | Location | Run Command | When to Use |
|-----------|----------|-------------|-------------|
| Unit (Python) | ``test/unit/`` | ``./run_tests.sh -unit`` | Isolated component tests |
| Unit (Client) | ``client/src/`` | ``make client-test`` | ES6/Vue component tests |
| API | ``lib/galaxy_test/api/`` | ``./run_tests.sh -api`` | Backend tests via API |
| Integration | ``test/integration/`` | ``./run_tests.sh -integration`` | Custom Galaxy config |
| Framework | ``test/functional/tools/`` | ``./run_tests.sh -framework`` | Tool XML testing |
| Workflow Framework | ``lib/galaxy_test/workflow/`` | ``./run_tests.sh -framework-workflows`` | Workflow evaluation |
| Selenium | ``lib/galaxy_test/selenium/`` | ``./run_tests.sh -selenium`` | UI tests (WebDriver) |
| Playwright | ``lib/galaxy_test/selenium/`` | ``./run_tests.sh -playwright`` | UI tests (Playwright) |
| Selenium Integration | ``test/integration_selenium/`` | ``./run_tests.sh -selenium`` | UI + custom config |

### Decision Tree

```
Does test need running Galaxy server?
├─ NO → Unit test
│       ├─ Python? → test/unit/ (pytest)
│       └─ Client? → client/src/ (Vitest)
└─ YES → Functional test
         Does test need web browser?
         ├─ NO → Does test need custom config?
         │       ├─ NO → Tool/workflow only?
         │       │       ├─ Tools → Framework test
         │       │       ├─ Workflows → Workflow Framework test
         │       │       └─ Neither → API test
         │       └─ YES → Integration test
         └─ YES → Does test need custom config?
                  ├─ NO → Selenium/Playwright test
                  └─ YES → Selenium Integration test
```

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
        via Vitest. Checkout [Frontend/ES6 Unit Tests](#es6_unit) below for more
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

            ***Does this test check only functionalities of Galaxy tools or workflows?***

            - **Yes, tools**

              In this case you do not actually need to deal with the Galaxy API
              directly and you can just create a Galaxy tool test to check that
              the required functionality does work as expected. These are called
              Galaxy tool framework tests and are located in
              ``test/functional/tools/``. Checkout
              [Tool Framework Tests](#framework) below for more information.

            - **Yes, workflows**

              Workflow framework tests verify workflow evaluation by running
              workflows and checking outputs. These are located in
              ``lib/galaxy_test/workflow/``. Checkout
              [Workflow Framework Tests](#workflow_framework) below for more
              information.

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
        a functional Galaxy server use browser automation to drive interaction
        with the Galaxy web interface. These tests can be run with either
        [Selenium](https://www.selenium.dev/) or [Playwright](https://playwright.dev/)
        as the browser driver. Both provide high level access to the Galaxy API
        like the tests above, and the frameworks take care of starting the
        Galaxy server.

        The choice between different frameworks comes down to the
        answer to the following question.

        ***Does this test require a special configuration of Galaxy?***

          - **No**

            These tests should be placed into ``lib/galaxy_test/selenium``
            and implemented using the [Selenium Tests](#selenium)
            framework described below. These same tests can also be run
            with [Playwright](#playwright) for faster execution.

          - **Yes**

            Tests that require both a very specific Galaxy configuration
            as well as the ability to drive a running Galaxy web interface
            should be placed into ``test/integration_selenium``. Checkout
            the [Selenium Integration Tests](#selenium_integration)
            information below for more information.

{#python_unit}
## Backend/Python Unit Tests

These are Python unit tests either defined inside of ``test/unit`` or
via doctests within a Python component. These should generally not require
a Galaxy instance and should quickly test just a component or a few
components of Galaxy's backend code.

### doctests to stand-alone tests?

doctests tend to be more brittle and more restrictive. I (@jmchilton)
would strongly suggest writing stand-alone unit testing files separate
from the code itself unless the tests are so clean and so isolated they
serve as high-quality documentation for the component under test.

### Slow 'Unit' Tests (External Dependency Management)

Tests in ``test/unit/tool_util/`` that interact with external services
(Conda, container registries, BioContainers) should be marked with
``@external_dependency_management``. This pytest marker is defined in
``test/unit/tool_util/util.py``:

```python
from .util import external_dependency_management

@external_dependency_management
def test_conda_install(tmp_path):
    # ... test conda operations
```

These tests are excluded from normal unit test runs. To run them:

```bash
tox -e mulled
# or directly:
pytest -m external_dependency_management test/unit/tool_util/
```

### Continuous Integration

The Python unit tests are run against each pull request to Galaxy using
CircleCI. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
CircleCI test definition for these tests is located in ``.circleci/config.yml``
below Galaxy's root.

{#es6_unit}
## Frontend/ES6 Unit Tests

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
``.github/workflows/client-unit.yaml`` below Galaxy's root.

{#framework}
## Tool Framework Tests

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
sample tool configuration XML (``test/functional/tools/sample_tool_conf.xml``).

General information on writing Galaxy Tool Tests can be found in Planemo's
documentation - for instance in the [Test-Driven Development](https://planemo.readthedocs.io/en/latest/writing_advanced.html#test-driven-development)
section.

### Continuous Integration

The Tool framework tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is fairly stable and typically there are not
transiently failed tests unrelated to the pull request being tested. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/framework_tools.yaml`` below Galaxy's root.

{#workflow_framework}
## Workflow Framework Tests

Similar to Tool Framework Tests, Workflow Framework Tests test Galaxy's
workflow evaluation engine by running workflows and verifying outputs.
These tests are located in ``lib/galaxy_test/workflow``.

Each workflow test consists of two files:

- A workflow definition file (``*.gxwf.yml``) in Galaxy's Format2 YAML syntax
- A test definition file (``*.gxwf-tests.yml``) containing test cases

### An Example

A simple workflow definition (``my_workflow.gxwf.yml``):

```yaml
class: GalaxyWorkflow
inputs:
  input_int:
    type: int
    default: 1
outputs:
  out:
    outputSource: my_tool/out_file1
steps:
  my_tool:
    tool_id: some_tool
    in:
      param1:
        source: input_int
```

And its corresponding test file (``my_workflow.gxwf-tests.yml``):

```yaml
- doc: |
    Test with default value
  job: {}
  outputs:
    out:
      class: File
      asserts:
      - that: has_text
        text: "expected content"

- doc: |
    Test with explicit input
  job:
    input_int: 42
  outputs:
    out:
      class: File
      asserts:
      - that: has_text
        text: "42"
```

Test cases can use ``expect_failure: true`` to verify that certain
inputs correctly cause workflow failures.

### Continuous Integration

The Workflow framework tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is fairly stable and typically there are not
transiently failed tests unrelated to the pull request being tested. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/framework_workflows.yaml`` below Galaxy's root.

{#api}
## API Tests

These tests are located in ``lib/galaxy_test/api`` and test various aspects
of the Galaxy API, as well as general backend aspects of Galaxy using the API.

### Test Class Structure

API tests inherit from ``ApiTestCase`` which provides the testing
infrastructure:

```python
from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase

class TestMyFeatureApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_something(self):
        history_id = self.dataset_populator.new_history()
        # ... test code
```

The ``ApiTestCase`` class (in ``lib/galaxy_test/api/_framework.py``) inherits from:

- ``FunctionalTestCase``: Handles server configuration and URL setup
- ``UsesApiTestCaseMixin``: Provides HTTP methods and API interaction utilities
- ``UsesCeleryTasks``: Configures async task handling

### HTTP Methods

The base class provides wrapped HTTP methods for API interaction:

```python
# GET request
response = self._get("histories")

# POST with data
response = self._post("histories", data={"name": "Test"})

# PUT, PATCH, DELETE
response = self._put(f"histories/{history_id}", data=payload)
response = self._patch(f"histories/{history_id}", data=updates)
response = self._delete(f"histories/{history_id}")

# Admin operations
response = self._get("users", admin=True)

# Run as different user (requires admin)
response = self._post("histories", data=data,
                      headers={"run-as": other_user_id}, admin=True)
```

### Populators

Populators are abstractions built on top of the Galaxy API that simplify
creating test data and fixtures. They're specifically designed for testing
use cases and provide a more convenient interface than directly using
``requests``.

The [``galaxy_test.base.populators`` module](../lib/galaxy_test.base.html#module-galaxy_test.base.populators) contains detailed docstrings
describing the concept and implementation of Populators.

#### DatasetPopulator

The most commonly used populator for creating and managing datasets:

```python
self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

# Create a new history
history_id = self.dataset_populator.new_history("Test History")

# Create a dataset with content
hda = self.dataset_populator.new_dataset(history_id, content="test data", wait=True)
dataset_id = hda["id"]

# Run a tool
result = self.dataset_populator.run_tool(
    tool_id="cat1",
    inputs={"input1": {"src": "hda", "id": dataset_id}},
    history_id=history_id
)
self.dataset_populator.wait_for_tool_run(history_id, result, assert_ok=True)

# Get HDA content - multiple ways to specify which HDA:

# By default, gets the most recent dataset in the history
content = self.dataset_populator.get_history_dataset_content(history_id)

# By history position (hid)
content = self.dataset_populator.get_history_dataset_content(history_id, hid=7)

# By HDA ID (encoded string)
content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=hda["id"])

# By passing a dataset object (dict) directly
content = self.dataset_populator.get_history_dataset_content(history_id, dataset=hda)

# Additional options:
# - wait=False: don't wait for history jobs to complete first
# - assert_ok=False: don't assert dataset reached 'ok' state
content = self.dataset_populator.get_history_dataset_content(
    history_id, hid=7, wait=True, assert_ok=False
)

# Get history content metadata (same option for specifying dataset available as get_history_dataset_content)
dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=hda["id"])
collection_details = self.dataset_populator.get_history_collection_details(history_id)
```

Despite its name, ``DatasetPopulator`` has become a central hub for abstractions
covering many Galaxy API operations beyond just datasets - including users, pages,
object stores, and more. When looking for a testing helper, check here first.

**The ``_raw`` Pattern**: Many populator methods come in pairs - a convenience
method that returns parsed JSON and a ``_raw`` variant that returns the raw
``Response`` object:

```python
# Convenience method: asserts success, returns parsed dict
result = self.dataset_populator.run_tool("cat1", inputs, history_id)
# result is a dict with 'jobs', 'outputs', etc.

# Raw method: returns Response for testing edge cases
response = self.dataset_populator.run_tool_raw("cat1", inputs, history_id)
assert_status_code_is(response, 200)
result = response.json()
```

Use raw methods when testing error responses, status codes, or API edge cases:

```python
# Testing error responses
response = self.workflow_populator.import_workflow_from_path_raw(workflow_path)
self._assert_status_code_is(response, 403)
self._assert_error_code_is(response, error_codes.error_codes_by_name["ADMIN_REQUIRED"])

# Testing permission denied
response = self.library_populator.show_ld_raw(library["id"], dataset["id"])
assert_status_code_is(response, 403)
assert_error_code_is(response, 403002)

# Testing validation errors
response = self.dataset_populator.create_landing_raw(invalid_request, "tool")
assert_status_code_is(response, 400)
assert "Field required" in response.json()["err_msg"]
```

Use non-raw methods for readable tests focused on functionality rather than
API response details.

#### WorkflowPopulator

For creating and executing workflows:

```python
self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

# Create a simple workflow
workflow_id = self.workflow_populator.simple_workflow("Test Workflow")

# Upload workflow from YAML
workflow_id = self.workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  step1:
    tool_id: cat1
    in:
      input1: input1
""")
```

#### DatasetCollectionPopulator

For creating dataset collections (lists, pairs, nested structures):

```python
self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

# Create a list collection
hdca = self.dataset_collection_populator.create_list_in_history(
    history_id,
    contents=["data1", "data2", "data3"],
    wait=True
)

# Create a paired collection
pair = self.dataset_collection_populator.create_pair_in_history(
    history_id,
    contents=[("forward", "ACGT"), ("reverse", "TGCA")],
    wait=True
)

# Create nested collections (list:paired)
identifiers = self.dataset_collection_populator.nested_collection_identifiers(
    history_id, "list:paired"
)
```

### API Test Assertions

The ``galaxy_test.base.api_asserts`` module provides assertion helpers:

```python
from galaxy_test.base.api_asserts import (
    assert_status_code_is,
    assert_status_code_is_ok,
    assert_has_keys,
    assert_not_has_keys,
    assert_error_code_is,
    assert_error_message_contains,
    assert_object_id_error,
)

# Check HTTP status codes
response = self._get("histories")
assert_status_code_is(response, 200)
assert_status_code_is_ok(response)  # Any 2XX

# Check response structure
data = response.json()
assert_has_keys(data[0], "id", "name", "state")
assert_not_has_keys(data[0], "admin_only_field")

# Check Galaxy error codes
error_response = self._post("invalid", data={})
assert_error_code_is(error_response, error_codes.USER_REQUEST_INVALID_PARAMETER)
assert_error_message_contains(error_response, "required field")

# Check invalid object ID handling (accepts 400 or 404)
fake_response = self._get("histories/invalid_id_12345")
assert_object_id_error(fake_response)
```

The test class also provides wrapper methods: ``self._assert_status_code_is()``,
``self._assert_has_keys()``, etc.

### Test Decorators

Common decorators for conditional test execution (from ``galaxy_test.base.decorators``):

```python
from galaxy_test.base.decorators import (
    requires_admin,
    requires_new_user,
    requires_new_history,
    requires_new_library,
)
from galaxy_test.base.populators import skip_without_tool

class TestMyApi(ApiTestCase):

    @requires_admin
    def test_admin_only_endpoint(self):
        # Test runs only with admin user
        ...

    @requires_new_user
    def test_fresh_user(self):
        # Creates new user for test isolation
        ...

    @requires_new_history
    def test_with_clean_history(self):
        # Ensures fresh history per test run
        ...

    @skip_without_tool("cat1")
    def test_cat_tool(self):
        # Skips if cat1 tool not installed
        ...
```

### Context Managers

#### User Switching

Test behavior with different users:

```python
def test_permissions(self):
    # Create resource as default user
    history_id = self.dataset_populator.new_history()

    # Test access as different user
    with self._different_user("other@example.com"):
        response = self._get(f"histories/{history_id}")
        self._assert_status_code_is(response, 403)

    # Test anonymous access
    with self._different_user(anon=True):
        response = self._get("histories")
        # Verify anonymous behavior
```

### Pytest Fixtures

Modern pytest-style tests can use fixtures from ``conftest.py``:

```python
# Session-scoped (expensive setup, reused)
def test_example(self, galaxy_interactor, dataset_populator):
    ...

# Request-scoped (fresh per test)
def test_with_history(self, history_id, target_history):
    hda = target_history.with_dataset("content").src_dict
    ...
```

Key fixtures:

| Fixture | Scope | Purpose |
|---------|-------|---------|
| ``galaxy_interactor`` | session | API interaction object |
| ``dataset_populator`` | session | Dataset creation helper |
| ``history_id`` | function | Fresh history per test |
| ``target_history`` | function | Fluent API for test data |
| ``required_tool`` | function | Tool fixture from markers |

### Async and Job Waiting

Wait for asynchronous operations:

```python
# Wait for history jobs to complete
self.dataset_populator.wait_for_history(history_id, assert_ok=True)

# Wait for specific job
job_id = result["jobs"][0]["id"]
self.dataset_populator.wait_for_job(job_id, assert_ok=True)

# Wait for workflow invocation
self.workflow_populator.wait_for_invocation(workflow_id, invocation_id)

# Wait for async task
self.dataset_populator.wait_on_task(async_response)
```

### Celery Tasks and Async Operations

Galaxy uses [Celery](https://docs.celeryq.dev/) for background task processing.
The ``ApiTestCase`` base class includes ``UsesCeleryTasks`` which automatically
configures Celery for testing. Many Galaxy operations return task responses
that must be awaited.

**Tool Requests**: Modern tool execution via ``/api/tool_requests`` returns
a task that must be awaited:

```python
# Submit tool request (async)
response = self.dataset_populator.tool_request_raw(tool_id, inputs, history_id)
response_json = response.json()

# Extract task info
tool_request_id = response_json["tool_request_id"]
task_result = response_json["task_result"]

# Wait for the Celery task to complete
self.dataset_populator.wait_on_task_object(task_result)

# Wait for the tool request to be submitted
state = self.dataset_populator.wait_on_tool_request(tool_request_id)
assert state  # True if submitted successfully

# Get the jobs created by the tool request
jobs = self.galaxy_interactor.jobs_for_tool_request(tool_request_id)
self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
```

**Short-Term Storage Downloads**: Export operations use short-term storage:

```python
# Request a history export
url = f"histories/{history_id}/prepare_store_download"
download_response = self._post(url, {"model_store_format": "tgz"}, json=True)

# Extract storage request ID
storage_request_id = self.dataset_populator.assert_download_request_ok(download_response)

# Wait for the download to be ready
self.dataset_populator.wait_for_download_ready(storage_request_id)

# Fetch the prepared file
content = self._get(f"short_term_storage/{storage_request_id}")
```

**Task ID Waiting**: For operations that return just a task ID:

```python
# Import returns a task ID
import_response = self._post("histories", {"archive_source": url})
task_id = import_response.json()["id"]

# Wait for task completion (returns True on SUCCESS, False on FAILURE)
task_ok = self.dataset_populator.wait_on_task_id(task_id)
assert task_ok, "Import task failed"
```

### Useful Example Files

| Pattern | Example File | What It Demonstrates |
|---------|--------------|----------------------|
| **Basic API structure** | ``lib/galaxy_test/api/test_roles.py`` | Simple GET/POST, admin vs. user |
| **Dataset operations** | ``lib/galaxy_test/api/test_datasets.py`` | Upload, search, update, delete |
| **Tool execution** | ``lib/galaxy_test/api/test_tool_execute.py`` | Modern fluent API patterns |
| **History import/export** | ``lib/galaxy_test/api/test_histories.py`` | Async tasks, short-term storage, reimport patterns |
| **User management** | ``lib/galaxy_test/api/test_users.py`` | Different user context, permissions |

### Continuous Integration

The API tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is fairly stable and typically there are not
transiently failed tests unrelated to the pull request being tested. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/api.yaml`` below Galaxy's root.

{#integration}
## Integration Tests

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


class TestQuotaIntegration(integration_util.IntegrationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_quotas"] = True

    #...
```

Integration test cases extend the ``IntegrationTestCase`` class defined in
the ``galaxy_test.driver.integration_util`` module (located in
``lib/galaxy_test/driver/integration_util.py``).

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

### API Utilities in Integration Tests

Integration tests have full access to all API testing utilities documented
in the [API Tests](#api) section above. This includes:

- **Populators**: ``DatasetPopulator``, ``WorkflowPopulator``, ``DatasetCollectionPopulator``
- **Assertions**: ``assert_status_code_is``, ``assert_has_keys``, ``assert_error_code_is``
- **HTTP Methods**: ``self._get()``, ``self._post()``, ``self._put()``, etc.
- **Context Managers**: ``self._different_user()``, ``self.dataset_populator.test_history()``
- **Decorators**: ``@requires_admin``, ``@skip_without_tool``

Review that section for details on these utilities.

### Class Attributes

Integration test classes support several class attributes that control
test setup:

```python
class TestMyFeature(integration_util.IntegrationTestCase):
    # Require the default API user to be an admin
    require_admin_user = True

    # Include Galaxy's sample tools and datatypes (for tool testing)
    framework_tool_and_types = True
```

| Attribute | Default | Purpose |
|-----------|---------|---------|
| ``require_admin_user`` | False | API user must be admin |
| ``framework_tool_and_types`` | False | Include sample tools/datatypes |

### Configuration Patterns

#### Direct Config Options

The simplest pattern sets config values directly:

```python
@classmethod
def handle_galaxy_config_kwds(cls, config):
    super().handle_galaxy_config_kwds(config)
    config["enable_quotas"] = True
    config["metadata_strategy"] = "extended"
    config["allow_path_paste"] = True
```

#### External Config Files

For complex configurations (job runners, object stores), reference
external files:

```python
import os

SCRIPT_DIRECTORY = os.path.dirname(__file__)
JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "my_job_conf.yml")

class TestCustomRunner(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_CONFIG_FILE
```

Common config file options:

- ``job_config_file`` - Job runner configuration (YAML or XML)
- ``object_store_config_file`` - Object store backends
- ``file_sources_config_file`` - Remote file sources
- ``container_resolvers_config_file`` - Container resolution

#### Dynamic Config with Templates

For configs requiring runtime values (temp directories, ports), use
``string.Template``:

```python
import string

OBJECT_STORE_TEMPLATE = string.Template("""
<object_store type="disk">
    <files_dir path="${temp_directory}/files"/>
    <extra_dir type="temp" path="${temp_directory}/tmp"/>
</object_store>
""")

class TestObjectStore(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_dir = cls._test_driver.mkdtemp()
        config_content = OBJECT_STORE_TEMPLATE.safe_substitute(
            temp_directory=temp_dir
        )
        config_path = os.path.join(temp_dir, "object_store_conf.xml")
        with open(config_path, "w") as f:
            f.write(config_content)
        config["object_store_config_file"] = config_path
```

#### Inline Dict Config

Job and container configs can also be specified as Python dicts:

```python
@classmethod
def handle_galaxy_config_kwds(cls, config):
    super().handle_galaxy_config_kwds(config)
    config.pop("job_config_file", None)  # Remove file-based config
    config["job_config"] = {
        "runners": {
            "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"}
        },
        "execution": {
            "default": "local_docker",
            "environments": {
                "local_docker": {"runner": "local", "docker_enabled": True}
            }
        }
    }
```

### Configuration Mixins

Galaxy provides mixin classes to simplify common configuration patterns.
Use multiple inheritance to compose capabilities:

```python
class TestWithObjectStore(
    integration_util.ConfiguresObjectStores,
    integration_util.IntegrationTestCase
):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(STORE_TEMPLATE, config)
```

| Mixin | Purpose | Key Methods |
|-------|---------|-------------|
| ``ConfiguresObjectStores`` | Object store setup | ``_configure_object_store()`` |
| ``ConfiguresDatabaseVault`` | Encrypted secrets | ``_configure_database_vault()`` |
| ``ConfiguresWorkflowScheduling`` | Workflow handlers | ``_configure_workflow_schedulers()`` |
| ``PosixFileSourceSetup`` | File upload sources | Auto-configures in ``handle_galaxy_config_kwds`` |

Example with ``PosixFileSourceSetup``:

```python
from galaxy_test.driver.integration_setup import PosixFileSourceSetup

class TestFileUploads(PosixFileSourceSetup, integration_util.IntegrationTestCase):
    # PosixFileSourceSetup auto-configures file sources
    # Override class attributes to customize:
    include_test_data_dir = True

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()  # Create test files
```

### Accessing Galaxy Internals

Integration tests can access Galaxy's application object directly via
``self._app``. This enables testing internal state not exposed via API.

#### Database Access

```python
from galaxy.model import StoredWorkflow
from sqlalchemy import select

def test_workflow_storage(self):
    # Query database directly
    stmt = select(StoredWorkflow).order_by(StoredWorkflow.id.desc()).limit(1)
    workflow = self._app.model.session.execute(stmt).scalar_one()

    # Access workflow internals
    assert workflow.latest_workflow.step_count == 3
```

#### Application Services

```python
def test_tool_data(self):
    # Access tool data tables
    table = self._app.tool_data_tables.get("all_fasta")
    entries = table.get_entries("dbkey", "hg38", "dbkey")

    # Access vault for secrets
    from galaxy.security.vault import UserVaultWrapper
    user_vault = UserVaultWrapper(self._app.vault, user)
    secret = user_vault.read_secret("my_secret")
```

#### Temporary Directory

```python
def test_with_temp_files(self):
    # Get managed temp directory (cleaned up after test)
    temp_dir = self._test_driver.mkdtemp()
    # or use self._tempdir property
```

### Skip Decorators

The ``integration_util`` module provides decorators for conditional
test execution:

```python
from galaxy_test.driver import integration_util

@integration_util.skip_unless_docker()
def test_docker_feature(self):
    ...

@integration_util.skip_unless_kubernetes()
def test_k8s_feature(self):
    ...

@integration_util.skip_unless_postgres()
def test_postgres_only(self):
    ...

@integration_util.skip_unless_amqp()
def test_with_message_queue(self):
    ...
```

| Decorator | Skips Unless |
|-----------|--------------|
| ``skip_unless_docker()`` | Docker available |
| ``skip_unless_kubernetes()`` | kubectl configured |
| ``skip_unless_postgres()`` | Using PostgreSQL |
| ``skip_unless_amqp()`` | AMQP URL configured |
| ``skip_if_github_workflow()`` | Not in GitHub Actions |
| ``skip_unless_environ(var)`` | Environment variable set |

### External Services

Some integration tests require external services (databases, message queues,
storage backends). These are either provided by CI infrastructure or started
as Docker containers by the tests themselves.

#### CI-Provided Services

The integration test GitHub workflow (``.github/workflows/integration.yaml``)
starts a Kubernetes pod with shared services:

| Service | Image | Port | Environment Variable |
|---------|-------|------|---------------------|
| PostgreSQL | ``postgres:17`` | 5432 | ``GALAXY_TEST_DBURI`` |
| RabbitMQ | ``rabbitmq`` | 5672 | ``GALAXY_TEST_AMQP_URL`` |

Tests requiring these services use skip decorators:

```python
@integration_util.skip_unless_postgres()
def test_postgres_feature(self):
    ...

@integration_util.skip_unless_amqp()
def test_celery_feature(self):
    ...
```

#### Docker Containers Started by Tests

Some tests start their own Docker containers in ``setUpClass`` and clean
them up in ``tearDownClass``. These require Docker to be available.

**Pattern for Docker-based tests:**

```python
@integration_util.skip_unless_docker()
class TestWithExternalService(integration_util.IntegrationTestCase):
    container_name: ClassVar[str]

    @classmethod
    def setUpClass(cls):
        cls.container_name = f"{cls.__name__}_container"
        # Start container
        subprocess.check_call([
            "docker", "run", "-d", "--rm",
            "--name", cls.container_name,
            "-p", "9000:9000",
            "minio/minio:latest", "server", "/data"
        ])
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        subprocess.check_call(["docker", "rm", "-f", cls.container_name])
        super().tearDownClass()
```

**Containers used in tests:**

| Image | Purpose | Test Files |
|-------|---------|------------|
| ``minio/minio:latest`` | S3-compatible storage | ``objectstore/`` tests |
| ``keycloak/keycloak:26.2`` | OIDC authentication | ``oidc/test_auth_oidc.py`` |
| ``mvdbeek/galaxy-integration-docker-images:slurm-22.01`` | Slurm scheduler | ``test_cli_runners.py`` |
| ``mvdbeek/galaxy-integration-docker-images:openpbs-22.01`` | PBS scheduler | ``test_cli_runners.py`` |
| ``savannah.ornl.gov/ndip/public-docker/rucio:1.29.8`` | Rucio data management | ``objectstore/`` tests |
| ``onedata/onezone:21.02.5-dev`` | Onedata storage | ``objectstore/`` tests |

**Environment variables for external services:**

Object store tests use environment variables for connection details:

```python
OBJECT_STORE_HOST = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_HOST", "127.0.0.1")
OBJECT_STORE_PORT = int(os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_PORT", 9000))
OBJECT_STORE_ACCESS_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_ACCESS_KEY", "minioadmin")
OBJECT_STORE_SECRET_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_SECRET_KEY", "minioadmin")
```

#### Kubernetes and Container Runtimes

The CI also sets up:

- **Minikube** - For ``test_kubernetes_runner.py``
- **Apptainer/Singularity** - Alternative container runtime for job tests

Tests skip appropriately when these aren't available:

```python
@integration_util.skip_unless_kubernetes()
def test_k8s_job(self):
    ...
```

### Useful Example Files

| Pattern | Example File | What It Demonstrates |
|---------|--------------|----------------------|
| **Simple config** | ``test/integration/test_quota.py`` | Basic ``handle_galaxy_config_kwds`` |
| **Job runners** | ``test/integration/test_job_environments.py`` | Job config, environment variables |
| **Object stores** | ``test/integration/objectstore/`` | Storage backends, S3/MinIO |
| **Workflows** | ``test/integration/test_workflow_tasks.py`` | Celery, export/import |
| **Database access** | ``test/integration/test_workflow_refactoring.py`` | SQLAlchemy ORM queries |
| **Containers** | ``test/integration/test_containerized_jobs.py`` | Docker/Singularity jobs |
| **File sources** | ``test/integration/test_remote_files.py`` | Remote file handling |
| **CLI runners** | ``test/integration/test_cli_runners.py`` | SSH/Slurm/PBS with Docker |
| **OIDC auth** | ``test/integration/oidc/test_auth_oidc.py`` | Keycloak integration |

### Continuous Integration

The Integration tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/integration.yaml`` below Galaxy's root.

{#selenium}
## Selenium Tests

These are full stack tests meant to test the Galaxy UI with real
browsers and are located in ``lib/galaxy_test/selenium``.

For detailed documentation on the browser automation framework architecture
(including protocol design, adding new browser operations, and building CLI tools),
see the [Browser Automation README](https://github.com/galaxyproject/galaxy/blob/dev/packages/selenium/README.rst).

### Jupyter + Selenium

Jupyter can leveraged to develop Selenium test cases interactively,
checkout out the [``galaxy_test.selenium.jupyter`` documentation](../lib/galaxy_test.selenium.jupyter)
for more a full discussion of this.

### API Abstractions Available

Selenium tests inherit all API test infrastructure. ``SeleniumTestCase`` includes
``dataset_populator``, ``dataset_collection_populator``, and ``workflow_populator``
just like API integration tests:

```python
class TestMyFeature(SeleniumTestCase):
    @selenium_test
    @managed_history
    def test_something(self):
        # API-based setup (fast, reliable)
        self.dataset_populator.new_dataset(self.history_id, content="test data")
        self.workflow_populator.upload_yaml_workflow(WORKFLOW_YAML)

        # UI interactions (what we're actually testing)
        self.components.history_panel.item(hid=1).wait_for_visible()
```

### When to Use UI vs API Methods

**Use API/populator methods** for test setup and auxiliary operations.
They're faster, more reliable, and won't introduce false failures from unrelated UI bugs.

**Use UI methods** when the UI interaction *is* what you're testing.

| Scenario | Use | Method |
|----------|-----|--------|
| Testing upload form | UI | ``self.perform_upload()`` |
| Need dataset for other test | API | ``self.dataset_populator.new_dataset()`` |
| Testing workflow editor | UI | ``self.workflow_run_open_workflow()`` |
| Need workflow for invocation test | API | ``self.workflow_populator.run_workflow()`` |
| Testing history panel display | UI | ``self.history_panel_click_item_title()`` |
| Need history with 10 datasets | API | loop with ``new_dataset()`` |

Example - testing dataset details panel (not upload):

```python
@selenium_test
@managed_history
def test_dataset_details_shows_metadata(self):
    # Setup via API - we're not testing uploads
    self.dataset_populator.new_dataset(
        self.history_id,
        content="chr1\t100\t200\ntest",
        file_type="bed",
    )

    # UI interaction - this IS what we're testing
    self.history_panel_wait_for_hid_ok(1)
    self.history_panel_click_item_title(hid=1)
    self.assert_item_dbkey_displayed_as(1, "?")
```

### Test Class Structure

Selenium tests inherit from ``SeleniumTestCase`` which combines browser automation
with Galaxy API access:

```python
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)

class TestMyFeature(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True  # Auto-login before each test

    @selenium_test
    @managed_history
    def test_something(self):
        self.perform_upload(self.get_filename("1.sam"))
        self.history_panel_wait_for_hid_ok(1)
        self.assert_item_summary_includes(1, "28 lines")
```

#### Class Attributes

| Attribute | Purpose |
|-----------|---------|
| ``ensure_registered`` | Auto-login before each test (uses ``GALAXY_TEST_SELENIUM_USER_EMAIL/PASSWORD`` or registers new user) |
| ``run_as_admin`` | Login as admin user instead |

#### Test Decorators

| Decorator | Purpose |
|-----------|---------|
| ``@selenium_test`` | Required wrapper - handles debug dumps on failure, retries (``GALAXY_TEST_SELENIUM_RETRIES``), baseline accessibility checks |
| ``@managed_history`` | Creates isolated named history per test, auto-cleanup after |
| ``@selenium_only(reason)`` | Skip test if running with Playwright backend |
| ``@playwright_only(reason)`` | Skip test if running with Selenium backend |

#### setup_with_driver()

Override this method for per-test setup that runs after driver initialization.
Gets re-executed on test retries and errors are automatically dumped for debugging:

```python
def setup_with_driver(self):
    super().setup_with_driver()
    self.perform_upload(self.get_filename("fixture.fasta"))
    self.wait_for_history()
```

### Smart Component System

Access UI elements through ``self.components``, a hierarchical tree that mirrors
Galaxy's UI structure. Components are defined in
``client/src/utils/navigation/navigation.yml`` and wrapped at runtime with
driver-aware methods via the ``SmartComponent`` and ``SmartTarget`` classes
(in ``lib/galaxy/selenium/smart_components.py``).

```python
# Access nested components via attribute chain
editor = self.components.workflow_editor
save_button = editor.save_button

# SmartTarget methods automatically wait and interact
save_button.wait_for_visible()       # Wait for visibility, return element
save_button.wait_for_and_click()     # Wait then click
save_button.assert_disabled()        # Verify disabled state

# Parameterized selectors
invocations = self.components.invocations
invocations.export_destination(destination="download").wait_for_and_click()
invocations.step_title(order_index="1").wait_for_visible()
```

Key ``SmartTarget`` methods:

| Method | Purpose |
|--------|---------|
| ``wait_for_visible()`` | Wait for visibility, return WebElement |
| ``wait_for_and_click()`` | Wait for visibility then click |
| ``wait_for_text()`` | Wait for visibility, return ``.text`` |
| ``wait_for_value()`` | Wait for visibility, return input value |
| ``wait_for_absent_or_hidden()`` | Wait for element to disappear |
| ``assert_absent_or_hidden()`` | Fail if element visible |
| ``assert_disabled()`` | Verify disabled state |
| ``all()`` | Return list of all matching elements |

For extending the component system or adding new operations, see the
[Browser Automation README](https://github.com/galaxyproject/galaxy/blob/dev/packages/selenium/README.rst).

### History and Workflow Operations

The test framework provides specialized methods for common Galaxy operations:

**File Uploads:**

```python
# Single file upload
self.perform_upload(self.get_filename("1.sam"))
self.perform_upload(self.get_filename("1.sam"), ext="txt", genome="hg18")

# Pasted content or URL
self.perform_upload_of_pasted_content("test data content")

# Collection uploads
self.upload_list([self.get_filename("1.tabular")], name="My List")
```

**History Panel:**

```python
self.history_panel_wait_for_hid_ok(1)              # Wait for job completion
self.history_panel_click_item_title(hid=1, wait=True)  # Expand item
self.wait_for_history()                            # Wait for all jobs
```

**Workflow Execution (via ``RunsWorkflows`` mixin):**

```python
class TestWorkflows(SeleniumTestCase, RunsWorkflows):
    @managed_history
    def test_workflow(self):
        self.perform_upload(self.get_filename("input.fasta"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_YAML)
        self.workflow_run_submit()
        self.workflow_run_wait_for_ok(hid=2, expand=True)
```

**Assertion Mixins:**

```python
# UsesHistoryItemAssertions
self.assert_item_summary_includes(hid, "expected text")
self.assert_item_name(hid, "expected_name")
self.assert_item_dbkey_displayed_as(hid, "hg18")

# UsesWorkflowAssertions
self._assert_showing_n_workflows(n)
```

### Accessibility Testing

The ``@selenium_test`` decorator automatically runs baseline accessibility
assertions after each test using [axe-core](https://www.deque.com/axe/).
Tests can also perform component-level accessibility checks:

```python
# Component-level assertion with impact threshold
login = self.components.login
login.form.assert_no_axe_violations_with_impact_of_at_least("moderate")

# With known violations excluded
VIOLATION_EXCEPTIONS = ["heading-order", "label"]
self.components.history_panel._.assert_no_axe_violations_with_impact_of_at_least(
    "moderate", VIOLATION_EXCEPTIONS
)
```

Impact levels: ``"minor"``, ``"moderate"``, ``"serious"``, ``"critical"``

For more on axe-core rules and impact levels, see the
[axe-core documentation](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md).

### Shared State Tests

For tests with expensive one-time setup (multiple users, published resources),
use ``SharedStateSeleniumTestCase``. The ``setup_shared_state()`` method runs
once per class, and state persists across all test methods:

```python
from .framework import selenium_test, SharedStateSeleniumTestCase

class TestPublishedPages(SharedStateSeleniumTestCase):
    @selenium_test
    def test_index(self):
        self.navigate_to_pages()
        assert len(self.get_grid_entry_names("#pages-published-grid")) == 2

    def setup_shared_state(self):
        # Called once before first test in class
        self.user1_email = self._get_random_email("test1")
        self.register(self.user1_email)
        self.new_public_page()
        self.logout_if_needed()

        self.user2_email = self._get_random_email("test2")
        self.register(self.user2_email)
        self.new_public_page()
```

### Useful Example Files

| Pattern | Example File | What It Demonstrates |
|---------|--------------|----------------------|
| **Basic structure** | ``lib/galaxy_test/selenium/test_login.py`` | Simple tests, accessibility |
| **History operations** | ``lib/galaxy_test/selenium/test_uploads.py`` | Uploads, history panel |
| **Workflow execution** | ``lib/galaxy_test/selenium/test_workflow_run.py`` | RunsWorkflows mixin |
| **Component patterns** | ``lib/galaxy_test/selenium/test_workflow_editor.py`` | Smart components |
| **Shared state** | ``lib/galaxy_test/selenium/test_published_pages.py`` | SharedStateSeleniumTestCase |
| **Admin tests** | ``lib/galaxy_test/selenium/test_admin_app.py`` | run_as_admin, admin UI |

### Configuration File

Both Selenium and Playwright tests can load configuration from a YAML file
using the ``GALAXY_TEST_END_TO_END_CONFIG`` environment variable. This is
useful for running tests against a running Galaxy server without hardcoding
credentials.

Copy and edit the sample config:

```bash
cp lib/galaxy_test/selenium/jupyter/galaxy_selenium_context.yml.sample ./galaxy_selenium_context.yml
```

Example config file:

```yaml
local_galaxy_url: http://localhost:8080
login_email: test_user@example.com
login_password: mycoolpassw0rd
# For remote Selenium (e.g., Docker):
#selenium_galaxy_url: http://host.docker.internal:8080
# For admin operations:
#admin_api_key: your_api_key
#admin_email: admin@example.com
#admin_password: admin_password
```

Config keys map to environment variables:

| Config Key | Environment Variable |
|------------|---------------------|
| ``local_galaxy_url`` | ``GALAXY_TEST_SELENIUM_URL`` |
| ``login_email`` | ``GALAXY_TEST_SELENIUM_USER_EMAIL`` |
| ``login_password`` | ``GALAXY_TEST_SELENIUM_USER_PASSWORD`` |
| ``admin_api_key`` | ``GALAXY_TEST_SELENIUM_ADMIN_API_KEY`` |
| ``selenium_galaxy_url`` | ``GALAXY_TEST_EXTERNAL_FROM_SELENIUM`` |

Usage:

```bash
GALAXY_TEST_END_TO_END_CONFIG=./galaxy_selenium_context.yml ./run_tests.sh -selenium
```

### Continuous Integration

The Selenium tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are 
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/selenium.yaml`` below Galaxy's root.

{#playwright}
## Playwright Tests

Playwright tests use the same test files as Selenium tests
(located in ``lib/galaxy_test/selenium``) but execute them using
[Playwright](https://playwright.dev/) instead of Selenium WebDriver.
Playwright offers faster execution and more reliable browser automation.

### Running Playwright Tests

Run all Playwright tests:

```bash
./run_tests.sh -playwright
```

Run specific Playwright tests:

```bash
./run_tests.sh -playwright lib/galaxy_test/selenium/test_workflow_editor.py
```

Run against a running Galaxy server (fastest for development):

```bash
./run.sh &  # run Galaxy on 8080
make client-dev-server &  # watch for client changes
export GALAXY_TEST_EXTERNAL=http://localhost:8081/
. .venv/bin/activate
GALAXY_TEST_DRIVER_BACKEND=playwright pytest lib/galaxy_test/selenium/test_login.py
```

Playwright requires browser installation:

```bash
playwright install chromium
```

### Continuous Integration

The Playwright tests are run against each pull request to Galaxy using
GitHub actions. If any of these tests fail, the pull request will be marked
red. This test suite is moderately prone to having tests fail that are
unrelated to the pull request being tested; if this test suite fails on
a pull request with changes that seem to be unrelated to the pull request -
ping the Galaxy committers on the pull request and request a re-run. The
GitHub actions workflow definition for these tests is located in
``.github/workflows/playwright.yaml`` below Galaxy's root.

{#selenium_integration}
## Selenium Integration Tests

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
``.github/workflows/integration_selenium.yaml`` below Galaxy's root.

{#transient_failures}
## Handling Flaky Tests

Some tests fail intermittently due to race conditions, timing issues, or external
dependencies. Galaxy provides infrastructure to track these "flaky" tests via
GitHub issues and a test decorator.

### Marking a Test as Transiently Failing

When a test is identified as flaky, create a GitHub issue with the
``transient-test-error`` label, then mark the test with the ``@transient_failure``
decorator:

```python
from galaxy.util.unittest_utils import transient_failure

@transient_failure(issue=21224)
@selenium_test
def test_sharing_private_history(self):
    # Test that sometimes fails due to race condition
    ...
```

When the test fails, the error message is modified to indicate this is a known
transient failure linked to a specific issue, helping CI reviewers quickly
identify non-blocking failures.

### Tracking Potential Fixes

When you implement a potential fix for a transient failure, update the decorator
with ``potentially_fixed=True``:

```python
@transient_failure(issue=21242, potentially_fixed=True)
def test_delete_job_with_message(self, history_id):
    ...
```

If the test fails after this flag is set, the error message will ask reviewers
to report the failure on the tracking issue with a timestamp. This helps
determine if fixes are effective and when issues can be closed.

### Workflow

1. Test fails intermittently in CI
2. Create GitHub issue with ``transient-test-error`` label
3. Add ``@transient_failure(issue=XXXXX)`` to the test
4. When a fix is implemented, add ``potentially_fixed=True``
5. If no failures are reported for ~1 month, close the issue and remove the decorator

### Legacy ``@flakey`` Decorator

The older ``@flakey`` decorator from ``galaxy_test.base.populators`` is still
present in some tests. Unlike ``@transient_failure``, it doesn't link to tracking
issues. When running with ``--skip_flakey_fails``, failures are converted to skips.
New flaky tests should use ``@transient_failure`` instead for better tracking.

{#running_tests}
## Running Python Tests

The best information about how to run Galaxy's Python tests can be
found in the help output of ``run_tests.sh --help``.

```{include} run_tests_help.txt
:literal:
```
