import json

from galaxy.webapps.galaxy.api.healthcheck import HealthCheckController


PASS = HealthCheckController.PASS
FAIL = HealthCheckController.FAIL
WARN = HealthCheckController.WARN


# helper class to create an object with attribute-style access from a dictionary
class AttributeNester:
    def __init__(self, input_dict):
        for key, val in input_dict.items():
            if isinstance(val, dict):
                val = AttributeNester(val)
            setattr(self, key, val)

    def __setitem__(self, key, value):
        self.__dict__[key] = value


# helper function to make a mock transaction object to simulate Galaxy states
def transmaker(worker_function, runners_dict):
    trans = AttributeNester({
        "app": {
            "application_stack": {
                "name": "MockWebWorker",
                "workers": worker_function},
            "job_manager": {
                "job_handler": {
                    "dispatcher": {
                        "job_runners": None}}}},
        "error_message": "",
        "anonymous": "",
        "request": {
            "body": ""},
        "response": {
            "headers": {
                "Cache-Control": "placeholder string"},
            "set_content_type": lambda arg, **kwargs: None,
            "status": "good?"
        },
        "debug": "",
        "status_code": 200
    })
    trans.app.job_manager.job_handler.dispatcher.job_runners = runners_dict
    return trans


# create base health check controller
hcc = HealthCheckController(AttributeNester(
    {
        "model": {
            "context": "contextless",
            "User": "MockUserModel"
        }
    }))


# general web worker mock-up
def _mock_workers(worker_count=3, status="idle", app=None):
    worker_template = {
        "id": 0,
        "status": status,
        "apps": app
    }
    result = []
    for w in range(worker_count):
        subresult = dict(worker_template)
        subresult["id"] = w
        result.append(subresult)
    return result


# general job runner mock-up
def _mock_job_runners(runner_count, nworkers):
    result = {}
    for r in range(runner_count):
        subresult = {
            "runner_name": "MockJobRunner",
            "nworkers": nworkers}
        result["MockJobRunner {}".format(r)] = AttributeNester(subresult)
    return result


# create mock healthy transaction object components
def _healthy_workers():
    return _mock_workers(3, "idle", ({"id": 0}))


def _healthy_job_runners():
    return _mock_job_runners(2, 2)


# create mock unhealthy transaction object components
def _unhealthy_workers_noapp():
    return _mock_workers(1, "idle", ())


def _unhealthy_workers_no_handlers():
    return []


def _unhealthy_workers_allfails():
    return _mock_workers(3, "fail", ({"id": 0}))


def _unhealthy_job_runners_noworkers():
    return _mock_job_runners(2, 0)


def _unhealthy_job_runners_norunner():
    return {}


def _half_healthy_job_runner():
    r = {}
    good_half = _mock_job_runners(1, 1)
    bad_half = _mock_job_runners(1, 0)
    values = list(bad_half.values()) + list(good_half.values())
    for n in range(len(values)):
        r["MockJobRunner {}".format(n)] = values[n]
    return r


def _half_healthy_web_workers():
    good_half = _mock_workers(1, "idle", ({"id": 0}))
    bad_half = _mock_workers(1, "neither idle nor busy", ({"id": 0}))
    return good_half + bad_half


def expected_webfail_checks(worker_number=0):
    return {
        'componentType': 'MockWebWorker worker',
        'status': FAIL,
        'notes': 'Web worker {} does not have a bound app'.format(worker_number),
        'componentId': 0}


expected_healthy_job_check_result = [
    {"componentType": "MockJobRunner", "status": PASS},
    {"componentType": "MockJobRunner", "status": PASS}]
expected_healthy_web_check_result = [
    {"componentType": "MockWebWorker worker", "status": PASS, "componentId": 0},
    {"componentType": "MockWebWorker worker", "status": PASS, "componentId": 1},
    {"componentType": "MockWebWorker worker", "status": PASS, "componentId": 2}]

expected_jobfail_notes = [
    'Job: 0 of 2 components pass health check',
    ' - MockJobRunner has status {}'.format(FAIL),
    ' - MockJobRunner has status {}'.format(FAIL)]
expected_jobfail_checks_notes = "Job runner 'MockJobRunner' has status '{}' - no workers found".format(FAIL)

expected_webfail_notes = [
    'Web: 0 of 1 components pass health check',
    ' - MockWebWorker worker:0 has status {}'.format(FAIL)]

expected_partial_job_notes = [
    'Job: 1 of 2 components pass health check',
    ' - MockJobRunner has status fail']
expected_partial_web_notes = ['Web: 3 of 3 components pass health check']


# test case: everything's good
def test_healthy_instance():
    healthy_trans = transmaker(_healthy_workers, _healthy_job_runners())
    expected_result = {
        "status": PASS,
        "notes": ["Job: 2 of 2 components pass health check", "Web: 3 of 3 components pass health check"],
        "checks": {
            "Web": expected_healthy_web_check_result,
            "Job": expected_healthy_job_check_result}}
    actual_result = json.loads(hcc.get(healthy_trans))
    assert expected_result == actual_result


# sub-test-case: web handler is good
def test_healthy_web():
    healthy_trans = transmaker(_healthy_workers, _healthy_job_runners())
    expected_result = {
        "status": PASS,
        "notes": ["Web: 3 of 3 components pass health check"],
        "checks": {
            "Web": expected_healthy_web_check_result}}
    actual_result = json.loads(hcc.get_web(healthy_trans))
    assert expected_result == actual_result


# sub-test-case: job runner is good
def test_healthy_job():
    healthy_trans = transmaker(_healthy_workers, _healthy_job_runners())
    expected_result = {
        "status": PASS,
        "notes": ["Job: 2 of 2 components pass health check"],
        "checks": {
            "Job": expected_healthy_job_check_result}}
    assert expected_result == json.loads(hcc.get_job(healthy_trans))


# run failure tests
#   NOTES:
# job runners fail by having no job runners or by being totally absent
# web runners fail by not being idle or busy, or by having no bound apps

# test case: job handler has no workers, web handler has no bound app
def test_failing_instance_noapp_noworker():
    failing_trans_job_workerless_web_appless = transmaker(_unhealthy_workers_noapp, _unhealthy_job_runners_noworkers())
    expected_result = {
        'status': FAIL,
        'notes': expected_jobfail_notes + expected_webfail_notes,
        'checks': {
            'Web': [expected_webfail_checks(0)],
            'Job': [
                {'componentType': 'MockJobRunner',
                 'status': FAIL,
                 'notes': expected_jobfail_checks_notes},
                {'componentType': 'MockJobRunner',
                 'status': FAIL,
                 'notes': expected_jobfail_checks_notes}]}}

    actual_result = json.loads(hcc.get(failing_trans_job_workerless_web_appless))
    assert expected_result == actual_result


# sub-test-case: job check with no workers
def test_failing_instance_noworker_job():
    failing_trans_job_workerless_web_appless = transmaker(_unhealthy_workers_noapp, _unhealthy_job_runners_noworkers())
    expected_result = {
        'status': FAIL,
        'notes': expected_jobfail_notes,
        'checks': {
            'Job': [
                {'componentType': 'MockJobRunner',
                 'status': FAIL,
                 'notes': expected_jobfail_checks_notes},
                {'componentType': 'MockJobRunner',
                 'status': FAIL,
                 'notes': expected_jobfail_checks_notes}]}}
    actual_result = json.loads(hcc.get_job(failing_trans_job_workerless_web_appless))
    assert expected_result == actual_result


# sub-test-case: web check with no bound app
def test_failing_instance_noapp_web():
    failing_trans_job_workerless_web_appless = transmaker(_unhealthy_workers_noapp, _unhealthy_job_runners_noworkers())
    expected_result = {
        'status': FAIL,
        'notes': expected_webfail_notes,
        'checks': {
            'Web': [
                {'componentType': 'MockWebWorker worker',
                 'status': FAIL,
                 'notes': 'Web worker 0 does not have a bound app',
                 'componentId': 0}]}}
    actual_result = json.loads(hcc.get_web(failing_trans_job_workerless_web_appless))
    assert expected_result == actual_result


# test case: no job handlers, no web handlers
def test_failing_instance_no_handlers():
    failing_trans_no_handlers = transmaker(_unhealthy_workers_no_handlers, _unhealthy_job_runners_norunner())
    expected_result = {
        'status': FAIL,
        'notes': [
            'Job: No components found',
            'Web: No components found'],
        'checks': {
            'Job': [
                {'status': FAIL, 'notes': ['Error: no Job handlers found']}],
            'Web': [
                {'status': FAIL, 'notes': ['Error: no Web handlers found']}]}}
    actual_result = json.loads(hcc.get(failing_trans_no_handlers))
    assert expected_result == actual_result


# sub-test-case: job check with no handlers
def test_failing_instance_no_handlers_job():
    failing_trans_no_handlers = transmaker(_unhealthy_workers_no_handlers, _unhealthy_job_runners_norunner())
    expected_result = {
        'status': FAIL,
        'notes': ['Job: No components found'],
        'checks': {'Job': [
            {'status': FAIL,
             'notes': ['Error: no Job handlers found']}]}}
    actual_result = json.loads(hcc.get_job(failing_trans_no_handlers))
    assert expected_result == actual_result


# sub-test-case: web check with no handlers
def test_failing_instance_no_handlers_web():
    failing_trans_no_handlers = transmaker(_unhealthy_workers_no_handlers, _unhealthy_job_runners_norunner())
    expected_result = {
        'status': FAIL,
        'notes': ['Web: No components found'],
        'checks': {'Web': [
            {'status': FAIL,
             'notes': ['Error: no Web handlers found']}]}}
    actual_result = json.loads(hcc.get_web(failing_trans_no_handlers))
    assert expected_result == actual_result


# test case: partial success in job, success in web
def test_partial_job_instance():
    warning_trans_iffy_jobs = transmaker(_healthy_workers, _half_healthy_job_runner())
    expected_result = {
        'status': WARN,
        'notes': expected_partial_job_notes + expected_partial_web_notes,
        'checks': {
            'Web': expected_healthy_web_check_result,
            'Job': [
                {'componentType': 'MockJobRunner',
                 'status': 'fail',
                 'notes': "Job runner 'MockJobRunner' has status 'fail' - no workers found"},
                {'componentType': 'MockJobRunner',
                 'status': 'pass'}]}}
    actual_result = json.loads(hcc.get(warning_trans_iffy_jobs))
    assert expected_result == actual_result


# sub-test-case: job handler group that is only half-healthy
def test_partial_job_instance_job():
    warning_trans_iffy_jobs = transmaker(_healthy_workers, _half_healthy_job_runner())
    expected_result = {
        'status': 'warn',
        'notes': expected_partial_job_notes,
        'checks': {
            'Job': [
                {'componentType': 'MockJobRunner',
                 'status': 'fail',
                 'notes': "Job runner 'MockJobRunner' has status 'fail' - no workers found"},
                {'componentType': 'MockJobRunner', 'status': 'pass'}]}}
    actual_result = json.loads(hcc.get_job(warning_trans_iffy_jobs))
    assert expected_result == actual_result


# test case: success in job, partial success in web
def test_partial_web_instance():
    warning_trans_iffy_web = transmaker(_half_healthy_web_workers, _healthy_job_runners())
    expected_result = {
        'status': 'warn',
        'notes': [
            'Job: 2 of 2 components pass health check',
            'Web: 1 of 2 components pass health check',
            ' - MockWebWorker worker:0 has status fail'],
        'checks': {
            'Web': [
                {'componentType': 'MockWebWorker worker', 'status': 'pass', 'componentId': 0},
                {'componentType': 'MockWebWorker worker', 'status': 'fail',
                 'notes': 'Web worker 0 status is neither idle nor busy', 'componentId': 0}],
            'Job': [
                {'componentType': 'MockJobRunner', 'status': 'pass'},
                {'componentType': 'MockJobRunner', 'status': 'pass'}]}}
    actual_result = json.loads(hcc.get(warning_trans_iffy_web))
    assert expected_result == actual_result


# sub-test-case: web worker that is only half-healthy
def test_partial_web_instance_web():
    warning_trans_iffy_web = transmaker(_half_healthy_web_workers, _healthy_job_runners())
    expected_result = {
        'status': 'warn',
        'notes': [
            'Web: 1 of 2 components pass health check',
            ' - MockWebWorker worker:0 has status fail'],
        'checks': {
            'Web': [
                {'componentType': 'MockWebWorker worker',
                 'status': 'pass', 'componentId': 0},
                {'componentType': 'MockWebWorker worker',
                 'status': 'fail',
                 'notes': 'Web worker 0 status is neither idle nor busy',
                 'componentId': 0}]}}
    actual_result = json.loads(hcc.get_web(warning_trans_iffy_web))
    assert expected_result == actual_result


# test case: both web and job handlers are half-healthy
def test_partial_web_and_job_instance():
    warning_trans_iffy_both = transmaker(_half_healthy_web_workers, _half_healthy_job_runner())
    expected_result = {
        'status': 'warn',
        'notes': [
            'Job: 1 of 2 components pass health check',
            ' - MockJobRunner has status fail',
            'Web: 1 of 2 components pass health check',
            ' - MockWebWorker worker:0 has status fail'],
        'checks': {
            'Web': [
                {'componentType': 'MockWebWorker worker',
                 'status': 'pass', 'componentId': 0},
                {'componentType': 'MockWebWorker worker', 'status': 'fail',
                 'notes': 'Web worker 0 status is neither idle nor busy',
                 'componentId': 0}],
            'Job': [
                {'componentType': 'MockJobRunner', 'status': 'fail',
                 'notes': "Job runner 'MockJobRunner' has status 'fail' - no workers found"},
                {'componentType': 'MockJobRunner', 'status': 'pass'}]}}
    actual_result = json.loads(hcc.get(warning_trans_iffy_both))
    assert expected_result == actual_result
