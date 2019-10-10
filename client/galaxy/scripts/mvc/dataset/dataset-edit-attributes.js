/** Dataset edit attributes view */
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
// import Utils from "utils/utils";
import Tabs from "mvc/ui/ui-tabs";
import Ui from "mvc/ui/ui-misc";
import Form from "mvc/form/form-view";

var View = Backbone.View.extend({
    initialize: function() {
        const Galaxy = getGalaxyInstance();
        this.setElement("<div/>");
        this.model = new Backbone.Model({
            dataset_id: Galaxy.params.dataset_id
        });
        this.message = new Ui.Message({ persistent: true });
        this.tabs = this._createTabs();
        this.active_tab = "user";
        this.$el
            .append($("<h4/>").append("Edit dataset attributes"))
            .append(this.message.$el)
            .append("<p/>")
            .append(this.tabs.$el)
            .hide();
        this.render();
    },

    /** fetch data for the selected dataset and build forms */
    render: function() {
        $.ajax({
            url: `${getAppRoot()}dataset/get_edit?dataset_id=${this.model.get("dataset_id")}`,
            success: response => {
                !this.initial_message && this.message.update(response);
                this.initial_message = true;
                _.each(this.forms, (form, key) => {
                    form.model.set("inputs", response[`${key}_inputs`]);
                    form.model.set("hide_operations", response[`${key}_disable`]);
                    form.render();
                });
                this.$el.show();
            },
            error: response => {
                var err_msg = response.responseJSON && response.responseJSON.err_msg;
                this.message.update({
                    status: "danger",
                    message: err_msg || "Error occurred while loading the dataset."
                });
            }
        });
    },

    /** submit data to backend to update attributes */
    _submit: function(operation, form) {
        var data = form.data.create();
        data.dataset_id = this.model.get("dataset_id");
        data.operation = operation;
        $.ajax({
            type: "PUT",
            url: `${getAppRoot()}dataset/set_edit`,
            data: data,
            success: response => {
                this.message.update(response);
                this.render();
                this._reloadHistory();
            },
            error: response => {
                var err_msg = response.responseJSON && response.responseJSON.err_msg;
                this.message.update({
                    status: "danger",
                    message: err_msg || "Error occurred while editing the dataset attributes."
                });
            }
        });
    },

    /** create tabs for different dataset attribute categories*/
    _createTabs: function() {
        this.forms = {
            attribute: this._getAttribute(),
            conversion: this._getConversion(),
            datatype: this._getDatatype(),
            permission: this._getPermission()
        };
        var tabs = new Tabs.View();
        tabs.add({
            id: "attribute",
            title: _l("Attributes"),
            icon: "fa fa-bars",
            tooltip: _l("Edit dataset attributes"),
            $el: this.forms.attribute.$el
        });
        tabs.add({
            id: "convert",
            title: _l("Convert"),
            icon: "fa-gear",
            tooltip: _l("Convert to new format"),
            $el: this.forms.conversion.$el
        });
        tabs.add({
            id: "datatype",
            title: _l("Datatypes"),
            icon: "fa-database",
            tooltip: _l("Change data type"),
            $el: this.forms.datatype.$el
        });
        tabs.add({
            id: "permissions",
            title: _l("Permissions"),
            icon: "fa-user",
            tooltip: _l("Permissions"),
            $el: this.forms.permission.$el
        });
        return tabs;
    },

    /** edit main attributes form */
    _getAttribute: function() {
        var form = new Form({
            title: _l("Edit attributes"),
            operations: {
                submit_attributes: new Ui.Button({
                    tooltip: _l("Save attributes of the dataset."),
                    icon: "fa-floppy-o",
                    title: _l("Save"),
                    onclick: () => {
                        this._submit("attributes", form);
                    }
                }),
                submit_autodetect: new Ui.Button({
                    tooltip:
                        "This will inspect the dataset and attempt to correct the values of fields if they are not accurate.",
                    icon: "fa-undo",
                    title: "Auto-detect",
                    onclick: () => {
                        this._submit("autodetect", form);
                    }
                })
            }
        });
        return form;
    },

    /** datatype conversion form */
    _getConversion: function() {
        var form = new Form({
            title: _l("Convert to new format"),
            operations: {
                submit_conversion: new Ui.Button({
                    tooltip: _l("Convert the datatype to a new format."),
                    title: _l("Convert datatype"),
                    icon: "fa-exchange",
                    onclick: () => {
                        this._submit("conversion", form);
                    }
                })
            }
        });
        return form;
    },

    /** change datatype form */
    _getDatatype: function() {
        var form = new Form({
            title: _l("Change datatype"),
            operations: {
                submit_datatype: new Ui.Button({
                    tooltip: _l("Change the datatype to a new type."),
                    title: _l("Change datatype"),
                    icon: "fa-exchange",
                    onclick: () => {
                        this._submit("datatype", form);
                    }
                }),
                submit_datatype_detect: new Ui.Button({
                    tooltip: _l("Detect the datatype and change it."),
                    title: _l("Detect datatype"),
                    icon: "fa-undo",
                    onclick: () => {
                        this._submit("datatype_detect", form);
                    }
                })
            }
        });
        return form;
    },

    /** dataset permissions form */
    _getPermission: function() {
        var form = new Form({
            title: _l("Manage dataset permissions"),
            operations: {
                submit_permission: new Ui.Button({
                    tooltip: _l("Save permissions."),
                    title: _l("Save permissions"),
                    icon: "fa-floppy-o ",
                    onclick: () => {
                        this._submit("permission", form);
                    }
                })
            }
        });
        return form;
    },

    /** reload Galaxy's history after updating dataset's attributes */
    _reloadHistory: function() {
        const Galaxy = getGalaxyInstance();
        if (Galaxy) {
            Galaxy.currHistoryPanel.loadCurrentHistory();
        }
    }
});

export default {
    View: View
};
