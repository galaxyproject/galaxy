/**
    This class creates input elements. New input parameter types should be added to the types dictionary.
*/
import Backbone from "backbone";
import DataPicker from "mvc/ui/ui-data-picker";
import SelectFtp from "mvc/ui/ui-select-ftp";
import SelectLibrary from "mvc/ui/ui-select-library";

// create form view
export default Backbone.View.extend({
    /** Available parameter types */
    types: {
        library_data: "_fieldLibrary",
        ftpfile: "_fieldFtp",
        data_dialog: "_fieldDialog",
    },

    remove: function () {
        this.field.remove();
        Backbone.View.prototype.remove.call(this);
    },

    /** Returns an input field for a given field type */
    create: function (input_def) {
        var fieldClass = this.types[input_def.type];
        this.field = typeof this[fieldClass] === "function" ? this[fieldClass].call(this, input_def) : null;
        if (input_def.value === undefined) {
            input_def.value = null;
        }
        this.field.value(input_def.value);
        this.setElement(input_def.el || "<div/>");
        this.$el.append(this.field.$el);
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
});
