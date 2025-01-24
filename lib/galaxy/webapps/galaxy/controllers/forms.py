import copy
import csv
import logging
import re

from sqlalchemy import (
    false,
    true,
)

from galaxy import model
from galaxy.managers.forms import get_form
from galaxy.model.index_filter_util import (
    raw_text_column_filter,
    text_column_filter,
)
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)
from galaxy.web.framework.helpers import grids
from galaxy.webapps.base.controller import (
    BaseUIController,
    web,
)

log = logging.getLogger(__name__)

VALID_FIELDNAME_RE = re.compile(r"^[a-zA-Z0-9\_]+$")


class FormsGrid(grids.GridData):
    # Custom column types
    class NameColumn(grids.GridColumn):
        def get_value(self, trans, grid, form):
            return form.latest_form.name

    class DescriptionColumn(grids.GridColumn):
        def get_value(self, trans, grid, form):
            return form.latest_form.desc

    class TypeColumn(grids.GridColumn):
        def get_value(self, trans, grid, form):
            return form.latest_form.type

    # Grid definition
    title = "Forms"
    model_class = model.FormDefinitionCurrent
    default_sort_key = "update_time"
    columns = [
        NameColumn(
            "Name",
            key="name",
            model_class=model.FormDefinition,
        ),
        DescriptionColumn("Description", key="desc", model_class=model.FormDefinition),
        TypeColumn("Type", key="type", model_class=model.FormDefinition),
        grids.GridColumn("Last Updated", key="update_time"),
        grids.GridColumn("Deleted", key="deleted", escape=False),
    ]

    def apply_query_filter(self, query, **kwargs):
        INDEX_SEARCH_FILTERS = {
            "name": "name",
            "description": "description",
            "is": "is",
        }
        deleted = False
        query = query.join(model.FormDefinition, self.model_class.latest_form_id == model.FormDefinition.id)
        if search_query := kwargs.get("search"):
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "name":
                        query = query.filter(text_column_filter(model.FormDefinition.name, term))
                    elif key == "description":
                        query = query.filter(text_column_filter(model.FormDefinition.desc, term))
                    elif key == "is":
                        if q == "deleted":
                            deleted = True
                elif isinstance(term, RawTextTerm):
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                model.FormDefinition.name,
                                model.FormDefinition.desc,
                            ],
                            term,
                        )
                    )
        query = query.filter(self.model_class.deleted == (true() if deleted else false()))
        return query


class Forms(BaseUIController):
    forms_grid = FormsGrid()

    @web.legacy_expose_api
    @web.require_admin
    def forms_list(self, trans, payload=None, **kwd):
        return self.forms_grid(trans, **kwd)

    @web.legacy_expose_api
    @web.require_admin
    def create_form(self, trans, payload=None, **kwd):
        if trans.request.method == "GET":
            fd_types = sorted(trans.app.model.FormDefinition.types.__members__.items())
            return {
                "title": "Create new form",
                "inputs": [
                    {"name": "name", "label": "Name"},
                    {"name": "desc", "label": "Description"},
                    {
                        "name": "type",
                        "type": "select",
                        "options": [(ft[1], ft[1]) for ft in fd_types],
                        "label": "Type",
                    },
                    {
                        "name": "csv_file",
                        "label": "Import from CSV",
                        "type": "upload",
                        "help": "Import fields from CSV-file with the following format: Label, Help, Type, Value, Options, Required=True/False.",
                        "optional": True,
                    },
                ],
            }
        else:
            # csv-file format: label, helptext, type, default, selectlist, required '''
            csv_file = payload.get("csv_file")
            index = 0
            if csv_file:
                lines = csv_file.splitlines()
                rows = csv.reader(lines)
                for row in rows:
                    if len(row) >= 6:
                        for column in range(len(row)):
                            row[column] = str(row[column]).strip('"')
                        prefix = f"fields_{index}|"
                        payload[f"{prefix}name"] = f"{index + 1}_imported_field"
                        payload[f"{prefix}label"] = row[0]
                        payload[f"{prefix}helptext"] = row[1]
                        payload[f"{prefix}type"] = row[2]
                        payload[f"{prefix}default"] = row[3]
                        payload[f"{prefix}selectlist"] = row[4]
                        payload[f"{prefix}required"] = row[5].lower() == "true"
                    index = index + 1
            new_form, message = self.save_form_definition(trans, None, payload)
            if new_form is None:
                return self.message_exception(trans, message)
            imported = (f" with {index} imported fields") if index > 0 else ""
            message = f"The form '{payload.get('name')}' has been created{imported}."
            return {"message": message}

    @web.legacy_expose_api
    @web.require_admin
    def edit_form(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No form id received for editing.")
        form = get_form(trans, id)
        latest_form = form.latest_form
        if trans.request.method == "GET":
            fd_types = sorted(trans.app.model.FormDefinition.types.__members__.items())
            ff_types = [(t.__name__, t.__name__) for t in trans.model.FormDefinition.supported_field_types]
            field_cache = []
            field_inputs = [
                {
                    "name": "name",
                    "label": "Name",
                    "value": "field_name",
                    "help": "The field name must be unique for each field and must contain only alphanumeric characters and underscore.",
                },
                {"name": "label", "label": "Label", "value": "Field label"},
                {"name": "helptext", "label": "Help text"},
                {"name": "type", "label": "Type", "type": "select", "options": ff_types},
                {"name": "default", "label": "Default value"},
                {
                    "name": "selectlist",
                    "label": "Options",
                    "help": "*Only for fields which allow multiple selections, provide comma-separated values.",
                },
                {"name": "required", "label": "Required", "type": "boolean", "value": False},
            ]
            form_dict = {
                "title": f"Edit form for '{latest_form.name}'",
                "inputs": [
                    {"name": "name", "label": "Name", "value": latest_form.name},
                    {"name": "desc", "label": "Description", "value": latest_form.desc},
                    {
                        "name": "type",
                        "type": "select",
                        "options": [(ft[1], ft[1]) for ft in fd_types],
                        "label": "Type",
                        "value": latest_form.type,
                    },
                    {
                        "name": "fields",
                        "title": "Field",
                        "type": "repeat",
                        "cache": field_cache,
                        "inputs": field_inputs,
                    },
                ],
            }
            for field in latest_form.fields:
                new_field = copy.deepcopy(field_inputs)
                for field_input in new_field:
                    field_value = field.get(field_input["name"])
                    if field_value:
                        if isinstance(field_value, list):
                            field_value = ",".join(field_value)
                        field_input["value"] = str(field_value)
                field_cache.append(new_field)
            return form_dict
        else:
            new_form, message = self.save_form_definition(trans, id, payload)
            if new_form is None:
                return self.message_exception(trans, message)
            message = f"The form '{payload.get('name')}' has been updated."
            return {"message": message}

    def get_current_form(self, trans, payload=None, **kwd):
        """
        This method gets all the unsaved user-entered form details and returns a
        dictionary containing the name, desc, type, layout & fields of the form
        """
        name = payload.get("name")
        desc = payload.get("desc") or ""
        type = payload.get("type")
        fields = []
        index = 0
        while True:
            prefix = f"fields_{index}|"
            if f"{prefix}label" in payload:
                field_attributes = ["name", "label", "helptext", "required", "type", "selectlist", "default"]
                field_dict = {attr: payload.get(f"{prefix}{attr}") for attr in field_attributes}
                field_dict["visible"] = True
                if isinstance(field_dict["selectlist"], str):
                    field_dict["selectlist"] = field_dict["selectlist"].split(",")
                else:
                    field_dict["selectlist"] = []
                fields.append(field_dict)
                index = index + 1
            else:
                break
        return dict(name=name, desc=desc, type=type, layout=[], fields=fields)

    def save_form_definition(self, trans, form_id=None, payload=None, **kwd):
        """
        This method saves a form given an id
        """
        if not payload.get("name"):
            return None, "Please provide a form name."
        if payload.get("type") == "none":
            return None, "Please select a form type."
        current_form = self.get_current_form(trans, payload)
        # validate fields
        field_names_dict = {}
        for field in current_form["fields"]:
            if not field["label"]:
                return None, "All the field labels must be completed."
            if not VALID_FIELDNAME_RE.match(field["name"]):
                return None, f"{field['name']} is not a valid field name."
            if field["name"] in field_names_dict:
                return None, f"Each field name must be unique in the form definition. {field['name']} is not unique."
            else:
                field_names_dict[field["name"]] = 1
        # create a new form definition
        form_definition = trans.app.model.FormDefinition(
            name=current_form["name"],
            desc=current_form["desc"],
            fields=current_form["fields"],
            form_definition_current=None,
            type=current_form["type"],
            layout=current_form["layout"],
        )
        # save changes to the existing form
        if form_id:
            form_definition_current = trans.sa_session.query(trans.app.model.FormDefinitionCurrent).get(
                trans.security.decode_id(form_id)
            )
            if form_definition_current is None:
                return None, f"Invalid form id ({form_id}) provided. Cannot save form."
        else:
            form_definition_current = trans.app.model.FormDefinitionCurrent()
        # create corresponding row in the form_definition_current table
        form_definition.form_definition_current = form_definition_current
        form_definition_current.latest_form = form_definition
        trans.sa_session.add(form_definition_current)
        trans.sa_session.commit()
        return form_definition, None
