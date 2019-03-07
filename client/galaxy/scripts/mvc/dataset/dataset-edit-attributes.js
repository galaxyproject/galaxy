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
        let Galaxy = getGalaxyInstance();
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
        var self = this;
        $.ajax({
            url: `${getAppRoot()}dataset/get_edit?dataset_id=${self.model.get("dataset_id")}`,
            success: function(response) {
                !self.initial_message && self.message.update(response);
                self.initial_message = true;
                _.each(self.forms, (form, key) => {
                    form.model.set("inputs", response[`${key}_inputs`]);
                    form.model.set("hide_operations", response[`${key}_disable`]);
                    form.render();
                });
                self.$el.show();
            },
            error: function(response) {
                var err_msg = response.responseJSON && response.responseJSON.err_msg;
                self.message.update({
                    status: "danger",
                    message: err_msg || "Error occurred while loading the dataset."
                });
            }
        });
    },

    /** submit data to backend to update attributes */
    _submit: function(operation, form) {
        var self = this;
        var data = form.data.create();
        data.dataset_id = this.model.get("dataset_id");
        data.operation = operation;
        $.ajax({
            type: "PUT",
            url: `${getAppRoot()}dataset/set_edit`,
            data: data,
            success: function(response) {
                self.message.update(response);
                self.render();
                self._reloadHistory();
            },
            error: function(response) {
                var err_msg = response.responseJSON && response.responseJSON.err_msg;
                self.message.update({
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
        var self = this;
        var form = new Form({
            title: _l("Edit attributes"),
            operations: {
                submit_attributes: new Ui.Button({
                    tooltip: _l("Save attributes of the dataset."),
                    icon: "fa-floppy-o",
                    title: _l("Save"),
                    onclick: function() {
                        self._submit("attributes", form);
                    }
                }),
                submit_autodetect: new Ui.Button({
                    tooltip:
                        "This will inspect the dataset and attempt to correct the values of fields if they are not accurate.",
                    icon: "fa-undo",
                    title: "Auto-detect",
                    onclick: function() {
                        self._submit("autodetect", form);
                    }
                })
            }
        });
        return form;
    },

    /** datatype conversion form */
    _getConversion: function() {
        var self = this;
        var form = new Form({
            title: _l("Convert to new format"),
            operations: {
                submit_conversion: new Ui.Button({
                    tooltip: _l("Convert the datatype to a new format."),
                    title: _l("Convert datatype"),
                    icon: "fa-exchange",
                    onclick: function() {
                        self._submit("conversion", form);
                    }
                })
            }
        });
        return form;
    },

    /** change datatype form */
    _getDatatype: function() {
        var self = this;
        var form = new Form({
            title: _l("Change datatype"),
            operations: {
                submit_datatype: new Ui.Button({
                    tooltip: _l("Change the datatype to a new type."),
                    title: _l("Change datatype"),
                    icon: "fa-exchange",
                    onclick: function() {
                        self._submit("datatype", form);
                    }
                }),
                submit_datatype_detect: new Ui.Button({
                    tooltip: _l("Detect the datatype and change it."),
                    title: _l("Detect datatype"),
                    icon: "fa-undo",
                    onclick: function() {
                        self._submit("datatype_detect", form);
                    }
                })
            }
        });
        return form;
    },

    /** dataset permissions form */
    _getPermission: function() {
        var self = this;
        var form = new Form({
            title: _l("Manage dataset permissions"),
            operations: {
                submit_permission: new Ui.Button({
                    tooltip: _l("Save permissions."),
                    title: _l("Save permissions"),
                    icon: "fa-floppy-o ",
                    onclick: function() {
                        self._submit("permission", form);
                    }
                })
            }
        });
        return form;
    },

    /** reload Galaxy's history after updating dataset's attributes */
    _reloadHistory: function() {
        let Galaxy = getGalaxyInstance();
        if (Galaxy) {
            Galaxy.currHistoryPanel.loadCurrentHistory();
        }
    }
});

export default {
    View: View
};
