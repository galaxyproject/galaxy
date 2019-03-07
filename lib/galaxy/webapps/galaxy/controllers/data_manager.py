import logging
from json import loads

import paste.httpexceptions
from six import string_types

import galaxy.queue_worker
from galaxy import web
from galaxy.util import nice_size, unicodify
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)


class DataManager(BaseUIController):

    @web.expose
    @web.json
    def data_managers_list(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = kwd.get('message', '')
        status = kwd.get('status', 'info')
        data_managers = []
        for data_manager_id, data_manager in sorted(trans.app.data_managers.data_managers.iteritems(),
                                                    key=lambda data_manager: data_manager[1].name):
            data_managers.append({'toolUrl': web.url_for(controller='root',
                                                         tool_id=data_manager.tool.id),
                                  'id': data_manager_id,
                                  'name': data_manager.name,
                                  'description': data_manager.description.lower()})
        data_tables = []
        managed_table_names = trans.app.data_managers.managed_data_tables.keys()
        for table_name in sorted(trans.app.tool_data_tables.get_tables().keys()):
            data_tables.append({'name': table_name,
                                'managed': True if table_name in managed_table_names else False})

        return {'dataManagers': data_managers,
                'dataTables': data_tables,
                'viewOnly': not_is_admin,
                'message': message,
                'status': status}

    @web.expose
    @web.json
    def jobs_list(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = kwd.get('message', '')
        status = kwd.get('status', 'info')
        data_manager_id = kwd.get('id', None)
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        if data_manager is None:
            return {'message': "Invalid Data Manager (%s) was requested" % data_manager_id,
                    'status': "error"}
        jobs = []
        for assoc in trans.sa_session.query(trans.app.model.DataManagerJobAssociation).filter_by(data_manager_id=data_manager_id):
            j = assoc.job
            jobs.append({
                'id': j.id,
                'encId': trans.security.encode_id(j.id),
                'runUrl': web.url_for(controller="tool_runner", action="rerun", job_id=trans.security.encode_id(j.id)),
                'user': j.history.user.email if j.history and j.history.user else "anonymous",
                'updateTime': j.update_time.isoformat(),
                'state': j.state,
                'commandLine': j.command_line,
                'jobRunnerName': j.job_runner_name,
                'jobRunnerExternalId': j.job_runner_external_id
            })
        jobs.reverse()
        return {'dataManager': {'name': data_manager.name,
                                'description': data_manager.description.lower(),
                                'toolUrl': web.url_for(controller='root',
                                                       tool_id=data_manager.tool.id)},
                'jobs': jobs,
                'viewOnly': not_is_admin,
                'message': message,
                'status': status}

    @web.expose
    @web.json
    def job_info(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = kwd.get('message', '')
        status = kwd.get('status', 'info')
        job_id = kwd.get('id', None)
        try:
            job_id = trans.security.decode_id(job_id)
            job = trans.sa_session.query(trans.app.model.Job).get(job_id)
        except Exception as e:
            job = None
            log.error("Bad job id (%s) passed to job_info: %s" % (job_id, e))
        if not job:
            return {'message': "Invalid job (%s) was requested" % job_id,
                    'status': "error"}
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = trans.app.data_managers.get_manager(data_manager_id)
        hdas = [assoc.dataset for assoc in job.get_output_datasets()]
        hda_info = []
        data_manager_output = []
        error_messages = []
        for hda in hdas:
            hda_info.append({'id': hda.id,
                             'encId': trans.security.encode_id(hda.id),
                             'name': hda.name,
                             'created': unicodify(hda.create_time.strftime(trans.app.config.pretty_datetime_format)),
                             'fileSize': nice_size(hda.dataset.file_size),
                             'fileName': hda.file_name,
                             'infoUrl': web.url_for(controller='dataset',
                                                    action='show_params',
                                                    dataset_id=trans.security.encode_id(hda.id))})
            try:
                data_manager_json = loads(open(hda.get_file_name()).read())
            except Exception as e:
                data_manager_json = {}
                error_messages.append("Unable to obtain data_table info for hda (%s): %s" % (hda.id, e))
            values = []
            for key, value in data_manager_json.get('data_tables', {}).items():
                values.append((key, value))
            data_manager_output.append(values)
        return {'jobId': job_id,
                'exitCode': job.exit_code,
                'runUrl': web.url_for(controller="tool_runner",
                                      action="rerun",
                                      job_id=trans.security.encode_id(job.id)),
                'commandLine': job.command_line,
                'dataManager': {'id': data_manager_id,
                                'name': data_manager.name,
                                'description': data_manager.description.lower(),
                                'toolUrl': web.url_for(controller='root',
                                                       tool_id=data_manager.tool.id)},
                'hdaInfo': hda_info,
                'dataManagerOutput': data_manager_output,
                'errorMessages': error_messages,
                'viewOnly': not_is_admin,
                'message': message,
                'status': status}

    @web.expose
    @web.json
    def tool_data_table_info(self, trans, **kwd):
        return self.tool_data_table_info_1(trans, **kwd)

    def tool_data_table_info_1(self, trans, **kwd):
        not_is_admin = not trans.user_is_admin
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized("This Galaxy instance is not configured to allow non-admins to view the data manager.")
        message = kwd.get('message', '')
        status = kwd.get('status', 'info')
        data_table_name = kwd.get('table_name', None)
        if not data_table_name:
            return {'message': "No data table was requested.",
                    'status': "error"}
        data_table = trans.app.tool_data_tables.get(data_table_name, None)
        if data_table is None:
            return {'message': "Invalid data table '%s' was requested." % data_table_name,
                    'status': "error"}
        return {'dataTable': {'name': data_table.name,
                              'columns': data_table.get_column_name_list(),
                              'data': data_table.data},
                'viewOnly': not_is_admin,
                'message': message,
                'status': status}

    @web.expose
    @web.json
    @web.require_admin
    def reload_tool_data_tables(self, trans, table_name=None, **kwd):
        if table_name and isinstance(table_name, string_types):
            table_name = table_name.split(",")
        # Reload the tool data tables
        table_names = self.app.tool_data_tables.reload_tables(table_names=table_name)
        galaxy.queue_worker.send_control_task(trans.app, 'reload_tool_data_tables',
                                              noop_self=True,
                                              kwargs={'table_name': table_name})
        data = None
        if table_names:
            message = "Reloaded data table%s '%s'." % ('s'[len(table_names) == 1:],
                                                       ', '.join(table_names))
            data = self.tool_data_table_info_1(trans,
                                               table_name=table_names[0],
                                               message=message,
                                               status="done")
        else:
            data = {'message': "No data tables have been reloaded.",
                    'status': "error"}
        return data

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
