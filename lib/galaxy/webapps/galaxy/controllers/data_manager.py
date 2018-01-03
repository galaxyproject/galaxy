import logging
from json import loads

import paste.httpexceptions
from markupsafe import escape
from six import string_types

import galaxy.queue_worker
from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)


class DataManager(BaseUIController):

    @web.expose
    @web.json
    def index(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = escape(kwd.get('message', ''))
        status = escape(kwd.get('status', 'info'))
        data_managers = trans.app.data_managers
        data_managers_items = list()
        if data_managers.data_managers:
            data_manager_items = data_managers.data_managers.iteritems()
            for data_manager_id, data_manager in sorted(data_manager_items, key=lambda x: x[1].name):
                data_manager_dict = {
                    "id": data_manager_id,
                    "tool_id": data_manager.tool.id,
                    "name": data_manager.name,
                    "description": data_manager.description
                }
                data_managers_items.append(data_manager_dict)
        tool_data_tables = trans.app.tool_data_tables
        tool_data_tables = sorted(tool_data_tables.get_tables().keys())
        managed_table_names = data_managers.managed_data_tables.keys()
        return {
            "data_managers": data_managers_items,
            "tool_data_tables": tool_data_tables,
            "managed_table_names": managed_table_names,
            "view_only": not_is_admin,
            "status": status,
            "message": message
        }

    @web.expose
    @web.json
    def manage_data_manager(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = escape(kwd.get('message', ''))
        status = escape(kwd.get('status', 'info'))
        data_manager_id = kwd.get('id', None)
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        if data_manager is None:
            return trans.response.send_redirect(web.url_for(controller="data_manager", action="index", message="Invalid Data Manager (%s) was requested" % data_manager_id, status="error"))
        jobs = list(reversed([assoc.job for assoc in trans.sa_session.query(trans.app.model.DataManagerJobAssociation).filter_by(data_manager_id=data_manager_id)]))
        jobs_list = list()
        for job in jobs:
            job_dict = {
                "id": job.id,
                "encoded_id": trans.security.encode_id(job.id),
                "history_user_email": job.history.user.email if job.history and job.history.user else 'anonymous',
                "update_time": str(job.update_time),
                "state": str(job.state),
                "command_line": str(job.command_line),
                "runner_name": str(job.job_runner_name),
                "runner_external_id": str(job.job_runner_external_id)
            }
            jobs_list.append(job_dict)

        return {
            "data_manager_name": data_manager.name,
            "data_manager_description": data_manager.description,
            "jobs": jobs_list,
            "view_only": not_is_admin,
            "message": message,
            "status": status
        }

    @web.expose
    @web.json
    def view_job(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = escape(kwd.get('message', ''))
        status = escape(kwd.get('status', 'info'))
        job_id = kwd.get('id', None)
        from galaxy.util import nice_size, unicodify
        try:
            job_id = trans.security.decode_id(job_id)
            job = trans.sa_session.query(trans.app.model.Job).get(job_id)
        except Exception as e:
            job = None
            log.error("Bad job id (%s) passed to view_job: %s" % (job_id, e))
        if not job:
            return trans.response.send_redirect(web.url_for(controller="data_manager", action="index", message="Invalid job (%s) was requested" % job_id, status="error"))
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        hdas = [assoc.dataset for assoc in job.get_output_datasets()]
        data_manager_output = []
        error_messages = []
        for hda in hdas:
            try:
                data_manager_json = loads(open(hda.get_file_name()).read())
            except Exception as e:
                data_manager_json = {}
                error_messages.append(escape("Unable to obtain data_table info for hda (%s): %s" % (hda.id, e)))
            values = []
            for key, value in data_manager_json.get('data_tables', {}).items():
                values.append((key, value))
            data_manager_output.append(values)

        hda_list = list()
        for hda in hdas:
            hda_dict = {
                "name": hda.name,
                "id": hda.id,
                "encoded_id": trans.security.encode_id(hda.id),
                "file_name": hda.file_name,
                "created_time": unicodify(hda.create_time.strftime(trans.app.config.pretty_datetime_format)),
                "file_size": nice_size(hda.dataset.file_size)
            }
            hda_list.append(hda_dict)

        return {
            "data_manager": {"tool_id": data_manager.tool.id, "name": data_manager.name, "description": data_manager.description},
            "job": {"encoded_id": trans.security.encode_id(job.id), "exit_code": str(job.exit_code)},
            "data_manager_output": data_manager_output,
            "hdas": hda_list,
            "view_only": not_is_admin,
            "message": message,
            "status": status,
            "error_messages": error_messages
        }

    @web.expose
    def manage_data_table(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = escape(kwd.get('message', ''))
        status = escape(kwd.get('status', 'info'))
        data_table_name = kwd.get('table_name', None)
        if not data_table_name:
            return trans.response.send_redirect(web.url_for(controller="data_manager", action="index"))
        data_table = trans.app.tool_data_tables.get(data_table_name, None)
        if data_table is None:
            return trans.response.send_redirect(web.url_for(controller="data_manager", action="index", message="Invalid Data table (%s) was requested" % data_table_name, status="error"))
        return trans.fill_template("data_manager/manage_data_table.mako", data_table=data_table, view_only=not_is_admin, message=message, status=status)

    @web.expose
    @web.require_admin
    def reload_tool_data_tables(self, trans, table_name=None, **kwd):
        if table_name and isinstance(table_name, string_types):
            table_name = table_name.split(",")
        # Reload the tool data tables
        table_names = self.app.tool_data_tables.reload_tables(table_names=table_name)
        galaxy.queue_worker.send_control_task(trans.app, 'reload_tool_data_tables',
                                              noop_self=True,
                                              kwargs={'table_name': table_name})
        redirect_url = None
        if table_names:
            status = 'done'
            if len(table_names) == 1:
                message = "The data table '%s' has been reloaded." % table_names[0]
                redirect_url = web.url_for(controller='data_manager',
                                           action='manage_data_table',
                                           table_name=table_names[0],
                                           message=message,
                                           status=status)
            else:
                message = "The data tables '%s' have been reloaded." % ', '.join(table_names)
        else:
            message = "No data tables have been reloaded."
            status = 'error'
        if redirect_url is None:
            redirect_url = web.url_for(controller='admin',
                                       action='view_tool_data_tables',
                                       message=message,
                                       status=status)
        return trans.response.send_redirect(redirect_url)

    @web.expose
    @web.json
    @web.require_admin
    def tool_data_table_items(self, trans, **kwd):
        data = {'columns': [], 'items': []}
        message = kwd.get('message', '')
        status = kwd.get('status', 'info')
        table_name = kwd.get('table_name', None)

        if not table_name:
            return {
                'data': data,
                'message': 'No Data table name provided.',
                'status': 'warning',
            }

        data_table = trans.app.tool_data_tables.get(table_name, None)

        if data_table is None:
            return {
                'data': data,
                'message': 'Invalid Data table (%s) was requested' % table_name,
                'status': 'error'
            }

        columns = data_table.get_column_name_list()
        rows = [dict(zip(columns, table_row)) for table_row in data_table.data]
        data['columns'] = columns
        data['items'] = rows

        return {'data': data, 'message': message, 'status': status}

    @web.expose
    @web.json
    @web.require_admin
    def reload_tool_data_table(self, trans, **kwd):
        table_name = kwd.get('table_name', None)

        if not table_name:
            return {
                'message': 'No data table has been reloaded.',
                'status': 'error',
            }

        redirect_url = web.url_for(
            controller='data_manager',
            action='tool_data_table_items',
            table_name=table_name,
            message='The data table "%s" has been reloaded.' % table_name,
            status='done',
        )

        return trans.response.send_redirect(redirect_url)
