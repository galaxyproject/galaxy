"""
FormDefinition and field factories
"""

# TODO: A FormDefinitionField is closely linked to a form_builder result.
# Can this functionality be further abstracted and merged with form_builder?
from galaxy.model import (
    FormDefinition,
    FormDefinitionCurrent,
)
from galaxy.util import string_as_bool

FORM_TYPES = {f_type.lower(): f_descript for f_type, f_descript in FormDefinition.types.__members__.items()}


class FormDefinitionFactory:
    def __init__(self, form_types, field_type_factories):
        self.form_types = form_types
        self.field_type_factories = field_type_factories

    def new(self, form_type, name, description=None, fields=None, layout=None, form_definition_current=None):
        """
        Return new FormDefinition.
        """
        assert (
            form_type in self.form_types
        ), f"Invalid FormDefinition type ( {form_type} not in {self.form_types.keys()} )"
        assert name, "FormDefinition requires a name"
        if description is None:
            description = ""
        if layout is None:
            layout = []
        if fields is None:
            fields = []
        # Create new FormDefinitionCurrent
        if form_definition_current is None:
            form_definition_current = FormDefinitionCurrent()
        rval = FormDefinition(
            name=name,
            desc=description,
            form_type=self.form_types[form_type],
            form_definition_current=form_definition_current,
            layout=layout,
            fields=fields,
        )
        form_definition_current.latest_form = rval
        return rval

    def from_elem(self, elem, form_definition_current=None):
        """
        Return FormDefinition created from an xml element.
        """
        name = elem.get("name", None)
        description = elem.get("description", None)
        form_type = elem.get("type", None)
        # load layout
        layout = []
        if layouts_elem := elem.find("layout"):
            for layout_elem in layouts_elem.findall("grid"):
                layout_name = layout_elem.get("name", None)
                assert layout_name and layout_name not in layout, "Layout grid element requires a unique name."
                layout.append(layout_name)
        # load fields
        fields = []
        if (fields_elem := elem.find("fields")) is not None:
            for field_elem in fields_elem.findall("field"):
                field_type = field_elem.get("type")
                assert field_type in self.field_type_factories, f"Invalid form field type ( {field_type} )."
                fields.append(self.field_type_factories[field_type].from_elem(field_elem, layout))
        # create and return new form
        return self.new(
            form_type,
            name,
            description=description,
            fields=fields,
            layout=layout,
            form_definition_current=form_definition_current,
        )


class FormDefinitionFieldFactory:
    type: str

    def __get_stored_field_type(self, **kwds):
        raise Exception("not implemented")

    def new(self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None):
        """
        Return new FormDefinition field.
        """
        rval = {}
        assert name, "Must provide a name"
        rval["name"] = name
        if not label:
            rval["label"] = name
        else:
            rval["label"] = label
        if required:
            rval["required"] = "required"
        else:
            rval["required"] = "optional"
        if helptext is None:
            helptext = ""
        rval["helptext"] = helptext
        if default is None:
            default = ""
        rval["default"] = default
        rval["visible"] = visible
        # if layout is None: #is this needed?
        #    layout = ''
        rval["layout"] = layout
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition created from an xml element.
        """
        name = elem.get("name")
        label = elem.get("label")
        required = string_as_bool(elem.get("required", "false"))
        default = elem.get("value")
        helptext = elem.get("helptext")
        visible = string_as_bool(elem.get("visible", "true"))
        field_layout = elem.get("layout", None)
        if field_layout:
            assert layout and field_layout in layout, f"Invalid layout specified: {field_layout} not in {layout}"
            field_layout = str(
                layout.index(field_layout)
            )  # existing behavior: integer indexes are stored as strings. why?
        return self.new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=field_layout,
        )


class FormDefinitionTextFieldFactory(FormDefinitionFieldFactory):
    type = "text"

    def __get_stored_field_type(self, area):
        if area:
            return "TextArea"
        else:
            return "TextField"

    def new(
        self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None, area=False
    ):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type(area)
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type(string_as_bool(elem.get("area", "false")))
        return rval


class FormDefinitionPasswordFieldFactory(FormDefinitionFieldFactory):
    type = "password"

    def __get_stored_field_type(self):
        return "PasswordField"

    def new(
        self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None, area=False
    ):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type()
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type()
        return rval


class FormDefinitionAddressFieldFactory(FormDefinitionFieldFactory):
    type = "address"

    def __get_stored_field_type(self):
        return "AddressField"

    def new(self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type()
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type()
        return rval


class FormDefinitionWorkflowFieldFactory(FormDefinitionFieldFactory):
    type = "workflow"

    def __get_stored_field_type(self):
        return "WorkflowField"

    def new(self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type()
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type()
        return rval


class FormDefinitionWorkflowMappingFieldFactory(FormDefinitionFieldFactory):
    type = "workflowmapping"

    def __get_stored_field_type(self):
        return "WorkflowMappingField"

    def new(self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type()
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type()
        return rval


class FormDefinitionHistoryFieldFactory(FormDefinitionFieldFactory):
    type = "history"

    def __get_stored_field_type(self):
        return "HistoryField"

    def new(self, name=None, label=None, required=False, helptext=None, default=None, visible=True, layout=None):
        """
        Return new FormDefinition field.
        """
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type()
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type()
        return rval


class FormDefinitionSelectFieldFactory(FormDefinitionFieldFactory):
    type = "select"

    def __get_stored_field_type(self, checkboxes):
        if checkboxes:
            return "CheckboxField"
        else:
            return "SelectField"

    def new(
        self,
        name=None,
        label=None,
        required=False,
        helptext=None,
        default=None,
        visible=True,
        layout=None,
        options=None,
        checkboxes=False,
    ):
        """
        Return new FormDefinition field.
        """
        options = options or []
        rval = super().new(
            name=name,
            label=label,
            required=required,
            helptext=helptext,
            default=default,
            visible=visible,
            layout=layout,
        )
        rval["type"] = self.__get_stored_field_type(checkboxes)
        if options is None:
            options = []
        rval["selectlist"] = options
        return rval

    def from_elem(self, elem, layout=None):
        """
        Return FormDefinition field created from an xml element.
        """
        rval = super().from_elem(elem, layout=layout)
        rval["type"] = self.__get_stored_field_type(string_as_bool(elem.get("checkboxes", "false")))
        # load select options
        rval["selectlist"] = []
        for select_option in elem.findall("option"):
            value = select_option.get("value", None)
            assert value is not None, 'Must provide a "value" for a select option'
            rval["selectlist"].append(value)
        return rval


field_type_factories = {
    field.type: field()
    for field in (
        FormDefinitionTextFieldFactory,
        FormDefinitionPasswordFieldFactory,
        FormDefinitionAddressFieldFactory,
        FormDefinitionSelectFieldFactory,
        FormDefinitionWorkflowFieldFactory,
        FormDefinitionWorkflowMappingFieldFactory,
        FormDefinitionHistoryFieldFactory,
    )
}

form_factory = FormDefinitionFactory(FORM_TYPES, field_type_factories)
