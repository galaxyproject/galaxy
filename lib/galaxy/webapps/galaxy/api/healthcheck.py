import logging

from galaxy.web import (
    expose_api_anonymous_and_sessionless
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class HealthCheckController(BaseAPIController):
    """
    controller for checking health
    """

    # status response strings
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"

    def __init__(self, app):
        super(HealthCheckController, self).__init__(app)

    @staticmethod
    def _handler_handler(handled, handler_type):
        if handled:
            return handled
        return [{
            "status": HealthCheckController.FAIL,
            "notes": ["Error: no {} handlers found".format(handler_type)]}]

    @staticmethod
    def _create_status_and_notes(result, service_string=None):
        if not result:
            result_string = "No components found"
            result_string = service_string + ": " + result_string
            return HealthCheckController.FAIL, [result_string]
        not_passing = 0
        status = HealthCheckController.PASS
        service_notes = []
        for r in result:
            if r["status"] != HealthCheckController.PASS:
                not_passing += 1
                service_notes.append(" - {}{} has status {}".format(
                    r["componentType"],
                    ":" + str(r["componentId"]) if "componentId" in r else "",
                    r["status"]))
        if not_passing:
            status = HealthCheckController.WARN if not_passing < len(result) else HealthCheckController.FAIL
        _l = len(result)
        notes = ["{} of {} components pass health check".format(_l - not_passing, _l)]
        notes.extend(service_notes)
        if service_string:
            notes[0] = service_string + ": " + notes[0]
        return status, notes

    @expose_api_anonymous_and_sessionless
    def get(self, trans, **kwargs):
        job_handler_result = self._get_job(trans)
        job_status, job_notes = self._create_status_and_notes(job_handler_result, "Job")
        worker_result = self._get_web(trans)
        worker_status, worker_notes = self._create_status_and_notes(worker_result, "Web")

        overall_status = HealthCheckController.PASS
        notes = list(job_notes)
        notes.extend(worker_notes)

        job_handler_result = self._handler_handler(job_handler_result, "Job")
        worker_result = self._handler_handler(worker_result, "Web")

        # if tests are not all passing
        if worker_status != HealthCheckController.PASS or job_status != HealthCheckController.PASS:
            # FAIL condition: if both are bad
            if worker_status == HealthCheckController.FAIL and job_status == HealthCheckController.FAIL:
                overall_status = HealthCheckController.FAIL
            # WARN condition: one at least passes
            else:
                overall_status = HealthCheckController.WARN
        return {
            "status": overall_status,
            "notes": notes,
            "checks": {
                "Job": job_handler_result,
                "Web": worker_result
            }
        }

    @staticmethod
    def _get_job(trans):
        job_notes_template = "Job runner '{}' has status '{}'{}"  # {}s = componentType, status, cause
        result = []
        runner_dict = trans.app.job_manager.job_handler.dispatcher.job_runners
        for key in runner_dict:
            _entry = runner_dict[key]
            subresult = {
                "componentType": _entry.runner_name,
                "status": HealthCheckController.PASS if _entry.nworkers > 0 else HealthCheckController.FAIL
            }
            if subresult["status"] != HealthCheckController.PASS:
                cause = " - no workers found"
                subresult["notes"] = job_notes_template.format(subresult["componentType"], subresult["status"], cause)
            result.append(subresult)
        return result

    @expose_api_anonymous_and_sessionless
    def get_job(self, trans, **kwargs):
        job_info = self._get_job(trans)
        job_status, job_notes = self._create_status_and_notes(job_info, "Job")
        job_info = self._handler_handler(job_info, "Job")
        return {
            "status": job_status,
            "notes": job_notes,
            "checks": {"Job": job_info}
        }

    @staticmethod
    def _get_web(trans):
        workers = trans.app.application_stack.workers()
        name = trans.app.application_stack.name
        if not workers:
            return []
        result = []
        for worker in workers:
            subresult = {
                "componentType": name + " worker",
                "componentId": worker['id'],
                "status": HealthCheckController.PASS
            }
            if worker['status'] not in ['busy', 'idle']:
                subresult["status"] = HealthCheckController.FAIL
                subresult["notes"] = "Web worker {} status is {}".format(worker['id'], worker['status'])
            elif 'apps' not in worker.keys() or not worker['apps']:
                subresult["status"] = HealthCheckController.FAIL
                subresult["notes"] = "Web worker {} does not have a bound app".format(worker['id'])
            result.append(subresult)
        return result

    @expose_api_anonymous_and_sessionless
    def get_web(self, trans, **kwargs):
        web_info = self._get_web(trans)
        checked_status, checked_notes = self._create_status_and_notes(web_info, "Web")
        web_info = self._handler_handler(web_info, "Web")
        return {
            "status": checked_status,
            "notes": checked_notes,
            "checks": {"Web": web_info}
        }
