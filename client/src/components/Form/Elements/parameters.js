/**
    This class creates input elements. New input parameter types should be added to the types dictionary.
*/
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import SelectContent from "mvc/ui/ui-select-content";
import SelectLibrary from "mvc/ui/ui-select-library";
import SelectFtp from "mvc/ui/ui-select-ftp";
import RulesEdit from "mvc/ui/ui-rules-edit";
import DataPicker from "mvc/ui/ui-data-picker";

// create form view
export default Backbone.View.extend({
    /** Available parameter types */
    types: {
        text: "_fieldText",
        password: "_fieldText",
        select: "_fieldSelect",
        data_column: "_fieldSelect",
        genomebuild: "_fieldSelect",
        data: "_fieldData",
        data_collection: "_fieldData",
        drill_down: "_fieldDrilldown",
        group_tag: "_fieldSelect",
        library_data: "_fieldLibrary",
        ftpfile: "_fieldFtp",
        upload: "_fieldUpload",
        rules: "_fieldRulesEdit",
        data_dialog: "_fieldDialog",
    },

    /** Returns an input field for a given field type */
    create: function (input_def) {
        const Galaxy = getGalaxyInstance();
        var fieldClass = this.types[input_def.type];
        this.field = typeof this[fieldClass] === "function" ? this[fieldClass].call(this, input_def) : null;
        if (!this.field) {
            this.field = input_def.options ? this._fieldSelect(input_def) : this._fieldText(input_def);
            Galaxy.emit.debug("form-parameters::_addRow()", `Auto matched field type (${input_def.type}).`);
        }
        if (input_def.value === undefined) {
            input_def.value = null;
        }
        this.field.value(input_def.value);
        this.setElement(input_def.el || "<div/>");
        this.$el.append(this.field.$el);
    },

    /** Data input field */
    _fieldData: function (input_def) {
        return new SelectContent.View({
            id: input_def.id,
            extensions: input_def.extensions,
            optional: input_def.optional,
            multiple: input_def.multiple,
            type: input_def.type,
            flavor: input_def.flavor,
            data: input_def.options,
            tag: input_def.tag,
            onchange: input_def.onchange,
        });
    },

    /** Select/Checkbox/Radio options field */
    _fieldSelect: function (input_def) {
        // show text field e.g. in workflow editor
        if (input_def.is_workflow) {
            return this._fieldText(input_def);
        }
        // customize properties
        if (input_def.type == "data_column") {
            input_def.error_text = "Missing columns in referenced dataset.";
        }

        // pick selection display
        var classes = {
            checkboxes: Ui.Checkbox,
            radio: Ui.Radio,
            radiobutton: Ui.RadioButton,
        };
        var SelectClass = classes[input_def.display] || Ui.Select;
        // use Select2 fields or regular select fields in workflow launch form?
        // check select_type_workflow_threshold option
        const Galaxy = getGalaxyInstance();
        var searchable = true;
        if (input_def.flavor == "workflow") {
            if (Galaxy.config.select_type_workflow_threshold == -1) {
                searchable = false;
            } else if (Galaxy.config.select_type_workflow_threshold == 0) {
                searchable = true;
            } else if (Galaxy.config.select_type_workflow_threshold < input_def.options.length) {
                searchable = false;
            }
        }
        return new Ui.TextSelect({
            id: input_def.id,
            data: input_def.data,
            options: input_def.options,
            display: input_def.display,
            error_text: input_def.error_text || "No options available",
            readonly: input_def.readonly,
            multiple: input_def.multiple,
            optional: input_def.optional,
            onchange: input_def.onchange,
            individual: input_def.individual,
            searchable: searchable,
            textable: input_def.textable,
            SelectClass: SelectClass,
        });
    },

    /** Drill down options field */
    _fieldDrilldown: function (input_def) {
        // show text field e.g. in workflow editor
        if (input_def.is_workflow) {
            return this._fieldText(input_def);
        }

        // create drill down field
        return new Ui.Drilldown.View({
            id: input_def.id,
            data: input_def.options,
            display: input_def.display,
            optional: input_def.optional,
            onchange: input_def.onchange,
        });
    },

    /** Text input field */
    _fieldText: function (input_def) {
        // field replaces e.g. a select field
        const inputClass = input_def.optional && input_def.type === "select" ? Ui.NullableText : Ui.Input;
        if (
            ["SelectTagParameter", "ColumnListParameter"].includes(input_def.model_class) ||
            (input_def.options && input_def.data)
        ) {
            input_def.area = input_def.multiple;
            if (Utils.isEmpty(input_def.value)) {
                input_def.value = null;
            } else {
                if (Array.isArray(input_def.value)) {
                    var str_value = "";
                    for (var i in input_def.value) {
                        str_value += String(input_def.value[i]);
                        if (!input_def.multiple) {
                            break;
                        }
                        str_value += "\n";
                    }
                    input_def.value = str_value;
                }
            }
        }
        // create input element
        return new inputClass({
            id: input_def.id,
            type: input_def.type,
            area: input_def.area,
            readonly: input_def.readonly,
            color: input_def.color,
            style: input_def.style,
            placeholder: input_def.placeholder,
            datalist: input_def.datalist,
            onchange: input_def.onchange,
            value: input_def.value,
        });
    },

    /** Data dialog picker field */
    _fieldDialog: function (input_def) {
        return new DataPicker({
            id: input_def.id,
            multiple: input_def.multiple,
            onchange: input_def.onchange,
        });
    },

    /** Library dataset field */
    _fieldLibrary: function (input_def) {
        return new SelectLibrary.View({
            id: input_def.id,
            optional: input_def.optional,
            multiple: input_def.multiple,
            onchange: input_def.onchange,
        });
    },

    /** FTP file field */
    _fieldFtp: function (input_def) {
        return new SelectFtp.View({
            id: input_def.id,
            optional: input_def.optional,
            multiple: input_def.multiple,
            onchange: input_def.onchange,
        });
    },

    _fieldRulesEdit: function (input_def) {
        return new RulesEdit.View({
            id: input_def.id,
            onchange: input_def.onchange,
            target: input_def.target,
        });
    },

    /** Upload file field */
    _fieldUpload: function (input_def) {
        return new Ui.Upload({
            id: input_def.id,
            onchange: input_def.onchange,
        });
    },
});
