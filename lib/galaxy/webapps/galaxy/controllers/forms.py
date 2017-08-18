import copy
import logging
import re

from markupsafe import escape
from galaxy import model, util
from galaxy.web.base.controller import BaseUIController, web
from galaxy.web.form_builder import FileField, TextField, HiddenField, SelectField
from galaxy.web.framework.helpers import iff, grids

log = logging.getLogger(__name__)

VALID_FIELDNAME_RE = re.compile("^[a-zA-Z0-9\_]+$")


class FormsGrid(grids.Grid):
    # Custom column types
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, form):
            return escape(form.latest_form.name)

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, form):
            return escape(form.latest_form.desc)

    class TypeColumn(grids.TextColumn):
        def get_value(self, trans, grid, form):
            return form.latest_form.type

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.deleted:
                return "deleted"
            return ""

    # Grid definition
    title = "Forms"
    model_class = model.FormDefinitionCurrent
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict(deleted="False")
    columns = [
        NameColumn("Name",
                   key="name",
                   model_class=model.FormDefinition,
                   link=(lambda item: iff(item.deleted, None, dict(action="view_form", id=item.id))),
                   attach_popup=True,
                   filterable="advanced"),
        DescriptionColumn("Description",
                          key='desc',
                          model_class=model.FormDefinition,
                          filterable="advanced"),
        TypeColumn("Type"),
        StatusColumn("Status"),
        grids.DeletedColumn("Deleted",
                            key="deleted",
                            visible=False,
                            filterable="advanced")
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0], columns[1]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    operations = [
        grids.GridOperation("Edit", allow_multiple=False, condition=(lambda item: not item.deleted), url_args=dict(controller="admin", action="form/edit_form")),
        grids.GridOperation("Delete", allow_multiple=True, condition=(lambda item: not item.deleted)),
        grids.GridOperation("Undelete", condition=(lambda item: item.deleted)),
    ]
    global_actions = [
        grids.GridAction("Create new form", dict(controller='admin', action='forms/create_form'))
    ]

    def build_initial_query(self, trans, **kwargs):
        return trans.sa_session.query(self.model_class).join(model.FormDefinition, self.model_class.latest_form_id == model.FormDefinition.id)


class Forms(BaseUIController):
    # Empty TextField
    empty_field = {'name': '',
                   'label': '',
                   'helptext': '',
                   'visible': True,
                   'required': False,
                   'type': model.TextField.__name__,
                   'selectlist': [],
                   'layout': 'none',
                   'default': ''}
    forms_grid = FormsGrid()

    @web.expose_api
    @web.require_admin
    def forms_list(self, trans, payload=None, **kwd):
        message = kwd.get('message', '')
        status = kwd.get('status', '')
        if 'operation' in kwd:
            id = kwd.get('id')
            if not id:
                return message_exception(trans, 'Invalid form id (%s) received.' % str(id))
            ids = util.listify(id)
            operation = kwd['operation'].lower()
            if operation == 'delete':
                message, status = self._delete_form(trans, ids)
            elif operation == 'undelete':
                message, status = self._undelete_form(trans, ids)
        if message and status:
            kwd['message'] = util.sanitize_text(message)
            kwd['status'] = status
        kwd['dict_format'] = True
        return self.forms_grid(trans, **kwd)

    @web.expose_api
    @web.require_admin
    def view_form(self, trans, **kwd):
        '''Displays the layout of the latest version of the form definition'''
        form_definition_current_id = kwd.get('id', None)
        try:
            form_definition_current = trans.sa_session.query(trans.app.model.FormDefinitionCurrent) \
                                                      .get(trans.security.decode_id(form_definition_current_id))
        except:
            return trans.response.send_redirect(web.url_for(controller='admin',
                                                            action='forms',
                                                            message='Invalid form',
                                                            status='error'))
        return trans.fill_template('/admin/forms/view_form_definition.mako',
                                   form_definition=form_definition_current.latest_form)

    @web.expose_api
    @web.require_admin
    def create_form(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get('message', ''))
        status = params.get('status', 'done')
        self.__imported_from_file = False
        if params.get('create_form_button', False):
            form_definition, message = self.save_form_definition(trans, form_definition_current_id=None, **kwd)
            if not form_definition:
                return trans.response.send_redirect(web.url_for(controller='forms',
                                                                action='create_form_definition',
                                                                message=message,
                                                                status='error',
                                                                name=util.restore_text(params.get('name', '')),
                                                                description=util.restore_text(params.get('description', ''))))
            if self.__imported_from_file:
                return trans.response.send_redirect(web.url_for(controller='forms',
                                                                action='edit_form_definition',
                                                                id=trans.security.encode_id(form_definition.current.id)))
            else:
                return trans.response.send_redirect(web.url_for(controller='forms',
                                                                action='edit_form_definition',
                                                                id=trans.security.encode_id(form_definition.current.id),
                                                                add_field_button='Add field',
                                                                name=form_definition.name,
                                                                description=form_definition.desc,
                                                                form_type_select_field=form_definition.type))
        inputs = [('Name', TextField('name', 40, util.restore_text(params.get('name', '')))),
                  ('Description', TextField('description', 40, util.restore_text(params.get('description', '')))),
                  ('Type', self.__build_form_types_widget(trans, selected=params.get('form_type', 'none'))),
                  ('Import from csv file (Optional)', FileField('file_data', 40, ''))]
        return trans.fill_template('/admin/forms/create_form.mako',
                                   inputs=inputs,
                                   message=message,
                                   status=status)

    @web.expose_api
    @web.require_admin
    def edit_form(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return message_exception(trans, 'No form id received for editing.')
        form = get_form(trans, id)
        latest_form = form.latest_form
        if trans.request.method == 'GET':
            fd_types = trans.app.model.FormDefinition.types.items()
            fd_types.sort()
            ff_types = [(t.__name__.replace( 'Field', ''), t.__name__) for t in trans.model.FormDefinition.supported_field_types]
            field_cache = []
            field_inputs = [{
                'name'    : 'name',
                'label'   : 'Name',
                'value'   : 'field_name',
                'help'    : 'The field name must be unique for each field and must contain only alphanumeric characters and underscore.'
            },{
                'name'    : 'label',
                'label'   : 'Label',
                'value'   : 'Field label'
            },{
                'name'    : 'helptext',
                'label'   : 'Help text'
            },{
                'name'    : 'type',
                'label'   : 'Type',
                'type'    : 'select',
                'options' : ff_types
            },{
                'name'    : 'selectlist',
                'label'   : 'Options',
                'help'    : '*Only for fields which allow multiple selections, provide comma-separated values.'
            },{
                'name'    : 'default',
                'label'   : 'Default value'
            },{
                'name'    : 'required',
                'label'   : 'Required',
                'type'    : 'boolean',
                'value'   : 'false'
            }]
            form_dict = {
                'title'  : 'Edit form for \'%s\'' % (util.sanitize_text(latest_form.name)),
                'inputs' : [{
                    'name'    : 'name',
                    'label'   : 'Name',
                    'value'   : latest_form.name
                }, {
                    'name'    : 'desc',
                    'label'   : 'Description',
                    'value'   : latest_form.desc
                }, {
                    'name'    : 'type',
                    'type'    : 'select',
                    'options' : [('None', 'none')] + [(ft[1], ft[1]) for ft in fd_types],
                    'label'   : 'Type',
                    'value'   : latest_form.type
                }, {
                    'name'    : 'fields',
                    'title'   : 'Field',
                    'type'    : 'repeat',
                    'cache'   : field_cache,
                    'inputs'  : field_inputs
                }]
            }
            for field in latest_form.fields:
                new_field = copy.deepcopy(field_inputs)
                for field_input in new_field:
                    field_value = field.get(field_input['name'])
                    if field_value:
                        if isinstance( field_value, list ):
                            field_value = ','.join(field_value)
                        field_input['value'] = str(field_value)
                field_cache.append(new_field)
            return form_dict
        else:
            try:
                return {'message': self._edit_quota(quota, util.Params(payload))}
            except Exception as e:
                return message_exception(trans, str(e))

                    new_form_definition, message = self.save_form_definition(trans, form_definition_current_id=form_definition.form_definition_current.id, **kwd)
            # if validation error encountered while saving the form, show the
            # unsaved form, with the error message
            if not new_form_definition:
                status = 'error'
            else:
                # everything went fine. form saved successfully. Show the saved form or redirect
                # to response_redirect if appropriate.
                if response_redirect:
                    return trans.response.send_redirect(response_redirect)
                form_definition = new_form_definition
                current_form = self.get_saved_form(form_definition)
                message = "The form '%s' has been updated with the changes." % form_definition.name

    def get_current_form(self, trans, **kwd):
        '''
        This method gets all the unsaved user-entered form details and returns a
        dictionary containing the name, desc, type, layout & fields of the form
        '''
        params = util.Params(kwd)
        name = util.restore_text(params.name)
        desc = util.restore_text(params.description) or ""
        form_type = util.restore_text(params.form_type_select_field)
        # get the user entered layout grids in it is a sample form definition
        layout = []
        if form_type == trans.model.FormDefinition.types.SAMPLE:
            index = 0
            while True:
                if 'grid_layout%i' % index in kwd:
                    grid_name = util.restore_text(params.get('grid_layout%i' % index, ''))
                    layout.append(grid_name)
                    index = index + 1
                else:
                    break
        # for csv file import
        csv_file = params.get('file_data', '')
        fields = []
        if csv_file == '':
            # get the user entered fields
            index = 0
            while True:
                if 'field_label_%i' % index in kwd:
                    fields.append(self.__get_field(index, **kwd))
                    index = index + 1
                else:
                    break
            fields = fields
        else:
            fields, layout = self.__import_fields(trans, csv_file, form_type)
        return dict(name=name,
                    desc=desc,
                    type=form_type,
                    layout=layout,
                    fields=fields)

    def save_form_definition(self, trans, form_definition_current_id=None, **kwd):
        '''
        This method saves the current form
        '''

        # check the form for invalid inputs
        if not util.restore_text(params.name):
            message_exception( trans, 'Form name must be filled.' )
        # form type
        if util.restore_text(params.form_type_select_field) == 'none':
            message_exception( trans, 'Form type must be selected.' )

        flag, message = self.__validate_form(**kwd)
        if not flag:
            return None, message
        current_form = self.get_current_form(trans, **kwd)
        # validate fields
        field_names_dict = {}
        for field in current_form['fields']:
            if not field['label']:
                return None, "All the field labels must be completed."
            if not VALID_FIELDNAME_RE.match(field['name']):
                return None, "'%s' is not a valid field name." % field['name']
            if field['name'] in field_names_dict:
                return None, "Each field name must be unique in the form definition. '%s' is not unique." % field['name']
            else:
                field_names_dict[field['name']] = 1
        # if type is sample form, it should have at least one layout grid
        if current_form['type'] == trans.app.model.FormDefinition.types.SAMPLE and not len(current_form['layout']):
            current_form['layout'] = ['Layout1']
        # create a new form definition
        form_definition = trans.app.model.FormDefinition(name=current_form['name'],
                                                         desc=current_form['desc'],
                                                         fields=current_form['fields'],
                                                         form_definition_current=None,
                                                         form_type=current_form['type'],
                                                         layout=current_form['layout'])
        if form_definition_current_id:  # save changes to the existing form
            # change the pointer in the form_definition_current table to point
            # to this new record
            form_definition_current = trans.sa_session.query(trans.app.model.FormDefinitionCurrent).get(form_definition_current_id)
        else:  # create a new form
            form_definition_current = trans.app.model.FormDefinitionCurrent()
        # create corresponding row in the form_definition_current table
        form_definition.form_definition_current = form_definition_current
        form_definition_current.latest_form = form_definition
        trans.sa_session.add(form_definition_current)
        trans.sa_session.flush()
        message = "The new form named '%s' has been created. " % (form_definition.name)
        return form_definition, message

    @web.expose
    @web.require_admin
    def _delete_form(self, trans, ids):
        for form_id in ids:
            form = get_form(trans, form_id)
            form.deleted = True
            trans.sa_session.add(form)
            trans.sa_session.flush()
        return ('Deleted %i form(s).' % len(ids), 'done')

    @web.expose
    @web.require_admin
    def _undelete_form(self, trans, ids):
        for form_id in ids:
            form = get_form(trans, form_id)
            form.deleted = False
            trans.sa_session.add(form)
            trans.sa_session.flush()
        return ('Undeleted %i form(s).' % len(ids), 'done')

    def __import_fields(self, trans, csv_file, form_type):
        '''
        "company","name of the company", "True", "required", "TextField",,
        "due date","turnaround time", "True", "optional", "SelectField","24 hours, 1 week, 1 month"
        '''
        import csv
        fields = []
        layouts = set()
        try:
            reader = csv.reader(csv_file.file)
            index = 1
            for row in reader:
                if len(row) < 7:  # ignore bogus rows
                    continue
                options = row[5].split(',')
                if len(row) >= 8:
                    fields.append({'name': '%i_field_name' % index,
                                   'label': row[0],
                                   'helptext': row[1],
                                   'visible': row[2],
                                   'required': row[3],
                                   'type': row[4],
                                   'selectlist': options,
                                   'layout': row[6],
                                   'default': row[7]})
                    layouts.add(row[6])
                else:
                    fields.append({'name': '%i_field_name' % index,
                                   'label': row[0],
                                   'helptext': row[1],
                                   'visible': row[2],
                                   'required': row[3],
                                   'type': row[4],
                                   'selectlist': options,
                                   'default': row[6]})
                index = index + 1
        except:
            return trans.response.send_redirect(web.url_for(controller='forms',
                                                            action='create_form',
                                                            status='error',
                                                            message='Error in importing <b>%s</b> file' % csv_file.file))
        self.__imported_from_file = True
        return fields, list(layouts)

# ---- Utility methods -------------------------------------------------------

def build_select_input(name, label, options, value):
    return {'type'      : 'select',
            'multiple'  : True,
            'optional'  : True,
            'individual': True,
            'name'      : name,
            'label'     : label,
            'options'   : options,
            'value'     : value}

def message_exception(trans, message):
    trans.response.status = 400
    return {'err_msg': util.sanitize_text(message)}

def get_form(trans, form_id):
    """Get a FormDefinition from the database by id."""
    form = trans.sa_session.query(trans.app.model.FormDefinitionCurrent).get(trans.security.decode_id(form_id))
    if not form:
        return trans.show_error_message("Form not found for id (%s)" % str(form_id))
    return form
