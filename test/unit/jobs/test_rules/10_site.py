from galaxy.jobs import JobDestination


def upload():
    return 'local_runner'


def tophat():
    return 'site_dest_id'


def tool1():
    # tool1 is id to test tool mocked out in test_mapper.py, without specify
    # function name in dynamic destination - this function should be used by
    # default.
    return 'tool1_dest_id'


def dynamic_chain_1():
    # Check whether chaining dynamic job destinations work
    return JobDestination(runner="dynamic",
                          params={'type': 'python',
                                  'function': 'dynamic_chain_2',
                                  'test_param': 'my_test_param'})


def dynamic_chain_2(test_param):
    # Check whether chaining dynamic job destinations work
    assert test_param == "my_test_param"
    return "final_destination"


def check_rule_params(
    job_id,
    tool,
    tool_id,
    job_wrapper,
    rule_helper,
    referrer,
    app,
    job,
    user,
    user_email,
):
    assert job_id == 12345
    assert tool.is_mock_tool()
    assert tool_id == "testtoolshed/devteam/tool1/23abcd13123"
    assert job_wrapper.is_mock_job_wrapper()
    assert app == job_wrapper.app
    assert rule_helper is not None
    assert isinstance(referrer, JobDestination)
    assert referrer.params['param1'] == "referrer_param"

    assert job.user == user
    assert user.id == 6789
    assert user_email == "test@example.com"

    return "all_passed"


def check_job_conf_params(param1):
    assert param1 == "7"
    return "sent_7_dest_id"


def check_resource_params(resource_params):
    assert resource_params["memory"] == "8gb"
    return "have_resource_params"


def check_workflow_invocation_uuid(workflow_invocation_uuid):
    return workflow_invocation_uuid
