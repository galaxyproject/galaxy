define("mvc/dataset/dataset-edit-attributes", ["exports", "utils/localization", "utils/utils", "mvc/ui/ui-tabs", "mvc/ui/ui-misc", "mvc/form/form-view"], function(exports, _localization, _utils, _uiTabs, _uiMisc, _formView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uiTabs2 = _interopRequireDefault(_uiTabs);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _formView2 = _interopRequireDefault(_formView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({
        initialize: function initialize() {
            this.setElement("<div/>");
            this.model = new Backbone.Model({
                dataset_id: Galaxy.params.dataset_id
            });
            this.message = new _uiMisc2.default.Message({
                persistent: true
            });
            this.tabs = this._createTabs();
            this.$el.append($("<h4/>").append("Edit dataset attributes")).append(this.message.$el).append("<p/>").append(this.tabs.$el).hide();
            this.render();
        },

        /** fetch data for the selected dataset and build forms */
        render: function render() {
            var self = this;
            $.ajax({
                url: Galaxy.root + "dataset/get_edit?dataset_id=" + self.model.get("dataset_id"),
                success: function success(response) {
                    !self.initial_message && self.message.update(response);
                    self.initial_message = true;
                    _.each(self.forms, function(form, key) {
                        form.model.set("inputs", response[key + "_inputs"]);
                        form.model.set("hide_operations", response[key + "_disable"]);
                        form.render();
                    });
                    self.$el.show();
                },
                error: function error(response) {
                    var err_msg = response.responseJSON && response.responseJSON.err_msg;
                    self.message.update({
                        status: "danger",
                        message: err_msg || "Error occured while loading the dataset."
                    });
                }
            });
        },

        /** submit data to backend to update attributes */
        _submit: function _submit(operation, form) {
            var self = this;
            var data = form.data.create();
            data.dataset_id = this.model.get("dataset_id");
            data.operation = operation;
            $.ajax({
                type: "PUT",
                url: Galaxy.root + "dataset/set_edit",
                data: data,
                success: function success(response) {
                    self.message.update(response);
                    self.render();
                    self._reloadHistory();
                },
                error: function error(response) {
                    var err_msg = response.responseJSON && response.responseJSON.err_msg;
                    self.message.update({
                        status: "danger",
                        message: err_msg || "Error occured while editing the dataset attributes."
                    });
                }
            });
        },

        /** create tabs for different dataset attribute categories*/
        _createTabs: function _createTabs() {
            this.forms = {
                attribute: this._getAttribute(),
                conversion: this._getConversion(),
                datatype: this._getDatatype(),
                permission: this._getPermission()
            };
            var tabs = new _uiTabs2.default.View();
            tabs.add({
                id: "attribute",
                title: (0, _localization2.default)("Attributes"),
                icon: "fa fa-bars",
                tooltip: (0, _localization2.default)("Edit dataset attributes"),
                $el: this.forms.attribute.$el
            });
            tabs.add({
                id: "convert",
                title: (0, _localization2.default)("Convert"),
                icon: "fa-gear",
                tooltip: (0, _localization2.default)("Convert to new format"),
                $el: this.forms.conversion.$el
            });
            tabs.add({
                id: "datatype",
                title: (0, _localization2.default)("Datatypes"),
                icon: "fa-database",
                tooltip: (0, _localization2.default)("Change data type"),
                $el: this.forms.datatype.$el
            });
            tabs.add({
                id: "permissions",
                title: (0, _localization2.default)("Permissions"),
                icon: "fa-user",
                tooltip: (0, _localization2.default)("Permissions"),
                $el: this.forms.permission.$el
            });
            return tabs;
        },

        /** edit main attributes form */
        _getAttribute: function _getAttribute() {
            var self = this;
            var form = new _formView2.default({
                title: (0, _localization2.default)("Edit attributes"),
                operations: {
                    submit_attributes: new _uiMisc2.default.ButtonIcon({
                        tooltip: (0, _localization2.default)("Save attributes of the dataset."),
                        icon: "fa-floppy-o",
                        title: (0, _localization2.default)("Save"),
                        onclick: function onclick() {
                            self._submit("attributes", form);
                        }
                    }),
                    submit_autodetect: new _uiMisc2.default.ButtonIcon({
                        tooltip: "This will inspect the dataset and attempt to correct the values of fields if they are not accurate.",
                        icon: "fa-undo",
                        title: "Auto-detect",
                        onclick: function onclick() {
                            self._submit("autodetect", form);
                        }
                    })
                }
            });
            return form;
        },

        /** datatype conversion form */
        _getConversion: function _getConversion() {
            var self = this;
            var form = new _formView2.default({
                title: (0, _localization2.default)("Convert to new format"),
                operations: {
                    submit_conversion: new _uiMisc2.default.ButtonIcon({
                        tooltip: (0, _localization2.default)("Convert the datatype to a new format."),
                        title: (0, _localization2.default)("Convert datatype"),
                        icon: "fa-exchange",
                        onclick: function onclick() {
                            self._submit("conversion", form);
                        }
                    })
                }
            });
            return form;
        },

        /** change datatype form */
        _getDatatype: function _getDatatype() {
            var self = this;
            var form = new _formView2.default({
                title: (0, _localization2.default)("Change datatype"),
                operations: {
                    submit_datatype: new _uiMisc2.default.ButtonIcon({
                        tooltip: (0, _localization2.default)("Change the datatype to a new type."),
                        title: (0, _localization2.default)("Change datatype"),
                        icon: "fa-exchange",
                        onclick: function onclick() {
                            self._submit("datatype", form);
                        }
                    })
                }
            });
            return form;
        },

        /** dataset permissions form */
        _getPermission: function _getPermission() {
            var self = this;
            var form = new _formView2.default({
                title: (0, _localization2.default)("Manage dataset permissions"),
                operations: {
                    submit_permission: new _uiMisc2.default.ButtonIcon({
                        tooltip: (0, _localization2.default)("Save permissions."),
                        title: (0, _localization2.default)("Save permissions"),
                        icon: "fa-floppy-o ",
                        onclick: function onclick() {
                            self._submit("permission", form);
                        }
                    })
                }
            });
            return form;
        },

        /** reload Galaxy's history after updating dataset's attributes */
        _reloadHistory: function _reloadHistory() {
            if (window.Galaxy) {
                window.Galaxy.currHistoryPanel.loadCurrentHistory();
            }
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-edit-attributes.js.map
