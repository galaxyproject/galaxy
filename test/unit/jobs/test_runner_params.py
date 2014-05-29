from galaxy.jobs import runners


def test_default_specs():
    # recheck_missing_job_retries is integer >= 0
    params = runners.RunnerParams( specs=runners.BaseJobRunner.DEFAULT_SPECS, params=dict( recheck_missing_job_retries="1" ) )
    assert params.recheck_missing_job_retries == 1
    assert params["recheck_missing_job_retries"] == 1

    exception_raised = False
    try:
        runners.RunnerParams( specs=runners.BaseJobRunner.DEFAULT_SPECS, params=dict( recheck_missing_job_retries=-1 ) )
    except Exception:
        exception_raised = True
    assert exception_raised


def test_missing_parameter():
    exception = None
    try:
        runners.RunnerParams( specs={}, params=dict( foo="bar" ) )
    except Exception as e:
        exception = e
    assert exception.message == runners.JOB_RUNNER_PARAMETER_UNKNOWN_MESSAGE % "foo"


def test_invalid_parameter():
    exception = None
    try:
        runners.RunnerParams( specs=dict( foo=dict( valid=lambda x: x != "bar", defualt="baz" ) ), params=dict( foo="bar" ) )
    except Exception as e:
        exception = e
    assert exception.message == runners.JOB_RUNNER_PARAMETER_VALIDATION_FAILED_MESSAGE % "foo"


def test_map_problem():
    exception = None
    try:
        runners.RunnerParams( specs=dict( foo=dict( map=lambda x: 1 / 0, default="baz" ) ), params=dict( foo="bar" ) )
    except Exception as e:
        exception = e
    assert exception.message == runners.JOB_RUNNER_PARAMETER_MAP_PROBLEM_MESSAGE % ( "foo", "bar" )


def test_param_default():
    runner_params = runners.RunnerParams( specs=dict( foo=dict( default="baz" ) ), params={} )
    assert runner_params["foo"] == "baz"
    assert runner_params.foo == "baz"
