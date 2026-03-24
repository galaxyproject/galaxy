import logging
from json import loads

import paste.httpexceptions

from galaxy import web
from galaxy.model import (
    DataManagerJobAssociation,
    Job,
)
from galaxy.util import (
    nice_size,
    unicodify,
)
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


class DataManager(BaseUIController):
    @web.expose
    @web.json
    def data_managers_list(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized(
                "This Galaxy instance is not configured to allow non-admins to view the data manager."
            )
        message = kwd.get("message", "")
        status = kwd.get("status", "info")
        data_managers = []
        for data_manager_id, data_manager in sorted(
            trans.app.data_managers.data_managers.items(), key=lambda dm: dm[1].name
        ):
            data_managers.append(
                {
                    "toolUrl": web.url_for(controller="root", tool_id=data_manager.tool.id),
                    "id": data_manager_id,
                    "name": data_manager.name,
                    "description": data_manager.description.lower(),
                }
            )
        data_tables = []
        managed_table_names = trans.app.data_managers.managed_data_tables.keys()
        for table_name in sorted(trans.app.tool_data_tables.get_tables().keys()):
            data_tables.append({"name": table_name, "managed": True if table_name in managed_table_names else False})

        return {
            "dataManagers": data_managers,
            "dataTables": data_tables,
            "viewOnly": not_is_admin,
            "message": message,
            "status": status,
        }

    @web.expose
    @web.json
    def jobs_list(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized(
                "This Galaxy instance is not configured to allow non-admins to view the data manager."
            )
        message = kwd.get("message", "")
        status = kwd.get("status", "info")
        data_manager_id = kwd.get("id", None)
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        if data_manager is None:
            return {"message": f"Invalid Data Manager ({data_manager_id}) was requested", "status": "error"}
        jobs = []
        for assoc in trans.sa_session.query(DataManagerJobAssociation).filter_by(data_manager_id=data_manager_id):
            j = assoc.job
            jobs.append(
                {
                    "id": j.id,
                    "encId": trans.security.encode_id(j.id),
                    "runUrl": web.url_for(
                        controller="tool_runner", action="rerun", job_id=trans.security.encode_id(j.id)
                    ),
                    "user": j.history.user.email if j.history and j.history.user else "anonymous",
                    "updateTime": j.update_time.isoformat(),
                    "state": j.state,
                    "commandLine": j.command_line,
                    "jobRunnerName": j.job_runner_name,
                    "jobRunnerExternalId": j.job_runner_external_id,
                }
            )
        jobs.reverse()
        return {
            "dataManager": {
                "name": data_manager.name,
                "description": data_manager.description.lower(),
                "toolUrl": web.url_for(controller="root", tool_id=data_manager.tool.id),
            },
            "jobs": jobs,
            "viewOnly": not_is_admin,
            "message": message,
            "status": status,
        }

    @web.expose
    @web.json
    def job_info(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized(
                "This Galaxy instance is not configured to allow non-admins to view the data manager."
            )
        message = kwd.get("message", "")
        status = kwd.get("status", "info")
        job_id = kwd.get("id", None)
        try:
            job_id = trans.security.decode_id(job_id)
            job = trans.sa_session.query(Job).get(job_id)
        except Exception as e:
            job = None
            log.error(f"Bad job id ({job_id}) passed to job_info: {e}")
        if not job:
            return {"message": f"Invalid job ({job_id}) was requested", "status": "error"}
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        hdas = [assoc.dataset for assoc in job.get_output_datasets()]
        hda_info = []
        data_manager_output = []
        error_messages = []
        for hda in hdas:
            hda_info.append(
                {
                    "id": hda.id,
                    "encId": trans.security.encode_id(hda.id),
                    "name": hda.name,
                    "created": unicodify(hda.create_time.strftime(trans.app.config.pretty_datetime_format)),
                    "fileSize": nice_size(hda.dataset.file_size),
                    "fileName": hda.get_file_name(),
                    "infoUrl": web.url_for(
                        controller="dataset", action="show_params", dataset_id=trans.security.encode_id(hda.id)
                    ),
                }
            )
            try:
                data_manager_json = loads(open(hda.get_file_name()).read())
            except Exception as e:
                data_manager_json = {}
                error_messages.append(f"Unable to obtain data_table info for hda ({hda.id}): {e}")
            values = []
            for key, value in data_manager_json.get("data_tables", {}).items():
                values.append((key, value))
            data_manager_output.append(values)
        return {
            "jobId": job_id,
            "exitCode": job.exit_code,
            "runUrl": web.url_for(controller="tool_runner", action="rerun", job_id=trans.security.encode_id(job.id)),
            "commandLine": job.command_line,
            "dataManager": {
                "id": data_manager_id,
                "name": data_manager.name,
                "description": data_manager.description.lower(),
                "toolUrl": web.url_for(controller="root", tool_id=data_manager.tool.id),
            },
            "hdaInfo": hda_info,
            "dataManagerOutput": data_manager_output,
            "errorMessages": error_messages,
            "viewOnly": not_is_admin,
            "message": message,
            "status": status,
        }
