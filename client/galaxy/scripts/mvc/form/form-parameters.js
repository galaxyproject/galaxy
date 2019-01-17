/**
    This class creates input elements. New input parameter types should be added to the types dictionary.
*/
import $ from "jquery";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import SelectContent from "mvc/ui/ui-select-content";
import SelectLibrary from "mvc/ui/ui-select-library";
import SelectFtp from "mvc/ui/ui-select-ftp";
import SelectGenomeSpace from "mvc/ui/ui-select-genomespace";
import RulesEdit from "mvc/ui/ui-rules-edit";
import ColorPicker from "mvc/ui/ui-color-picker";

// create form view
export default Backbone.Model.extend({
    /** Available parameter types */
    types: {
        text: "_fieldText",
        password: "_fieldText",
        select: "_fieldSelect",
        data_column: "_fieldSelect",
        genomebuild: "_fieldSelect",
        data: "_fieldData",
        data_collection: "_fieldData",
        integer: "_fieldSlider",
        float: "_fieldSlider",
        boolean: "_fieldBoolean",
        drill_down: "_fieldDrilldown",
        color: "_fieldColor",
        hidden: "_fieldHidden",
        hidden_data: "_fieldHidden",
        baseurl: "_fieldHidden",
        library_data: "_fieldLibrary",
        ftpfile: "_fieldFtp",
        upload: "_fieldUpload",
        rules: "_fieldRulesEdit",
        genomespacefile: "_fieldGenomeSpace"
    },

    /** Returns an input field for a given field type */
    create: function(input_def) {
        let Galaxy = getGalaxyInstance();
        var fieldClass = this.types[input_def.type];
        var field = typeof this[fieldClass] === "function" ? this[fieldClass].call(this, input_def) : null;
        if (!field) {
            field = input_def.options ? this._fieldSelect(input_def) : this._fieldText(input_def);
            Galaxy.emit.debug("form-parameters::_addRow()", `Auto matched field type (${input_def.type}).`);
        }
        if (input_def.value === undefined) {
            input_def.value = null;
        }
        field.value(input_def.value);
        return field;
    },

    /** Data input field */
    _fieldData: function(input_def) {
        return new SelectContent.View({
            id: `field-${input_def.id}`,
            extensions: input_def.extensions,
            optional: input_def.optional,
            multiple: input_def.multiple,
            type: input_def.type,
            flavor: input_def.flavor,
            data: input_def.options,
            onchange: input_def.onchange
        });
    },

    /** Select/Checkbox/Radio options field */
    _fieldSelect: function(input_def) {
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
            radiobutton: Ui.RadioButton
        };
        var SelectClass = classes[input_def.display] || Ui.Select;
        return new Ui.TextSelect({
            id: `field-${input_def.id}`,
            data: input_def.data,
            options: input_def.options,
            display: input_def.display,
            error_text: input_def.error_text || "No options available",
            readonly: input_def.readonly,
            multiple: input_def.multiple,
            optional: input_def.optional,
            onchange: input_def.onchange,
            individual: input_def.individual,
            searchable: input_def.flavor !== "workflow",
            textable: input_def.textable,
            SelectClass: SelectClass
        });
    },

    /** Drill down options field */
    _fieldDrilldown: function(input_def) {
        // show text field e.g. in workflow editor
        if (input_def.is_workflow) {
            return this._fieldText(input_def);
        }

        // create drill down field
        return new Ui.Drilldown.View({
            id: `field-${input_def.id}`,
            data: input_def.options,
            display: input_def.display,
            optional: input_def.optional,
            onchange: input_def.onchange
        });
    },

    /** Text input field */
    _fieldText: function(input_def) {
        // field replaces e.g. a select field
        if (input_def.options && input_def.data) {
            input_def.area = input_def.multiple;
            if (Utils.isEmpty(input_def.value)) {
                input_def.value = null;
            } else {
                if ($.isArray(input_def.value)) {
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
        return new Ui.Input({
            id: `field-${input_def.id}`,
            type: input_def.type,
            area: input_def.area,
            readonly: input_def.readonly,
            placeholder: input_def.placeholder,
            datalist: input_def.datalist,
            onchange: input_def.onchange
        });
    },

    /** Slider field */
    _fieldSlider: function(input_def) {
        return new Ui.Slider.View({
            id: `field-${input_def.id}`,
            precise: input_def.type == "float",
            is_workflow: input_def.is_workflow,
            min: input_def.min,
            max: input_def.max,
            onchange: input_def.onchange
        });
    },

    /** Hidden field */
    _fieldHidden: function(input_def) {
        return new Ui.Hidden({
            id: `field-${input_def.id}`,
            info: input_def.info
        });
    },

    /** Boolean field */
    _fieldBoolean: function(input_def) {
        return new Ui.RadioButton.View({
            id: `field-${input_def.id}`,
            data: [{ label: "Yes", value: "true" }, { label: "No", value: "false" }],
            onchange: input_def.onchange
        });
    },

    /** Color picker field */
    _fieldColor: function(input_def) {
        return new ColorPicker({
            id: `field-${input_def.id}`,
            onchange: input_def.onchange
        });
    },

    /** Library dataset field */
    _fieldLibrary: function(input_def) {
        return new SelectLibrary.View({
            id: `field-${input_def.id}`,
            optional: input_def.optional,
            multiple: input_def.multiple,
            onchange: input_def.onchange
        });
    },

    /** FTP file field */
    _fieldFtp: function(input_def) {
        return new SelectFtp.View({
            id: `field-${input_def.id}`,
            optional: input_def.optional,
            multiple: input_def.multiple,
            onchange: input_def.onchange
        });
    },

    /** GenomeSpace file select field
     */
    _fieldGenomeSpace: function(input_def) {
        return new SelectGenomeSpace.View({
            id: `field-${input_def.id}`,
            onchange: input_def.onchange
        });
    },

    _fieldRulesEdit: function(input_def) {
        return new RulesEdit.View({
            id: `field-${input_def.id}`,
            onchange: input_def.onchange,
            target: input_def.target
        });
    },

    /** Upload file field */
    _fieldUpload: function(input_def) {
        return new Ui.Upload({
            id: `field-${input_def.id}`,
            onchange: input_def.onchange
        });
    }
});
