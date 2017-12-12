define("mvc/ui/ui-select-content", ["exports", "utils/localization", "utils/utils", "mvc/ui/ui-misc", "mvc/ui/ui-select-default"], function(exports, _localization, _utils, _uiMisc, _uiSelectDefault) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _uiSelectDefault2 = _interopRequireDefault(_uiSelectDefault);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Batch mode variations */
    var Batch = {
        DISABLED: "disabled",
        ENABLED: "enabled",
        LINKED: "linked"
    };

    /** List of available content selectors options */
    var Configurations = {
        data: [{
            src: "hda",
            icon: "fa-file-o",
            tooltip: (0, _localization2.default)("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED
        }, {
            src: "hda",
            icon: "fa-files-o",
            tooltip: (0, _localization2.default)("Multiple datasets"),
            multiple: true,
            batch: Batch.LINKED
        }, {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: (0, _localization2.default)("Dataset collection"),
            multiple: false,
            batch: Batch.LINKED
        }],
        data_multiple: [{
            src: "hda",
            icon: "fa-files-o",
            tooltip: (0, _localization2.default)("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED
        }, {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: (0, _localization2.default)("Dataset collections"),
            multiple: true,
            batch: Batch.DISABLED
        }],
        data_collection: [{
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: (0, _localization2.default)("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED
        }],
        workflow_data: [{
            src: "hda",
            icon: "fa-file-o",
            tooltip: (0, _localization2.default)("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED
        }],
        workflow_data_multiple: [{
            src: "hda",
            icon: "fa-files-o",
            tooltip: (0, _localization2.default)("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED
        }],
        workflow_data_collection: [{
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: (0, _localization2.default)("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED
        }],
        module_data: [{
            src: "hda",
            icon: "fa-file-o",
            tooltip: (0, _localization2.default)("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED
        }, {
            src: "hda",
            icon: "fa-files-o",
            tooltip: (0, _localization2.default)("Multiple datasets"),
            multiple: true,
            batch: Batch.ENABLED
        }],
        module_data_collection: [{
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: (0, _localization2.default)("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED
        }, {
            src: "hdca",
            icon: "fa-folder",
            tooltip: (0, _localization2.default)("Multiple collections"),
            multiple: true,
            batch: Batch.ENABLED
        }]
    };

    /** View for hda and hdca content selector ui elements */
    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                src_labels: {
                    hda: "dataset",
                    hdca: "dataset collection"
                },
                pagelimit: 100,
                statustimer: 1000
            }).set(options);
            this.setElement($("<div/>").addClass("ui-select-content"));
            this.button_product = new _uiMisc2.default.RadioButton.View({
                value: "false",
                data: [{
                    icon: "fa fa-chain",
                    value: "false",
                    tooltip: "Linked inputs will be run in matched order with other datasets e.g. use this for matching forward and reverse reads."
                }, {
                    icon: "fa fa-chain-broken",
                    value: "true",
                    tooltip: "Unlinked dataset inputs will be run against *all* other inputs."
                }]
            });
            var $batch_div = $("<div/>").addClass("ui-form-info").append($("<i/>").addClass("fa fa-sitemap")).append($("<span/>").html("This is a batch mode input field. Separate jobs will be triggered for each dataset selection."));
            this.$batch = {
                linked: $batch_div.clone(),
                enabled: $batch_div.clone().append($("<div/>").append($("<div/>").addClass("ui-form-title").html("Batch options:")).append(this.button_product.$el)).append($("<div/>").css("clear", "both"))
            };

            // add drag-drop event handlers
            this.$el.on("dragenter", function(e) {
                this.lastenter = e.target;
                self.$el.addClass("ui-dragover");
            }).on("dragover", function(e) {
                e.preventDefault();
            }).on("dragleave", function(e) {
                this.lastenter === e.target && self.$el.removeClass("ui-dragover");
            }).on("drop", function(e) {
                self._handleDrop(e);
            });

            // track current history elements
            this.history = {};

            // add listeners
            this.listenTo(this.model, "change:data", this._changeData, this);
            this.listenTo(this.model, "change:wait", this._changeWait, this);
            this.listenTo(this.model, "change:current", this._changeCurrent, this);
            this.listenTo(this.model, "change:value", this._changeValue, this);
            this.listenTo(this.model, "change:type change:optional change:multiple change:extensions", this._changeType, this);
            this.render();

            // add change event
            this.on("change", function() {
                options.onchange && options.onchange(self.value());
            });
        },

        render: function render() {
            this._changeType();
            this._changeValue();
            this._changeWait();
        },

        /** Indicate that select fields are being updated */
        wait: function wait() {
            this.model.set("wait", true);
        },

        /** Indicate that the options update has been completed */
        unwait: function unwait() {
            this.model.set("wait", false);
        },

        /** Update data representing selectable options */
        update: function update(options) {
            this.model.set("data", options);
        },

        /** Return the currently selected dataset values */
        value: function value(new_value) {
            new_value !== undefined && this.model.set("value", new_value);
            var current = this.model.get("current");
            if (this.config[current]) {
                var id_list = this.fields[current].value();
                if (id_list !== null) {
                    id_list = $.isArray(id_list) ? id_list : [id_list];
                    if (id_list.length > 0) {
                        var result = this._batch({
                            values: []
                        });
                        for (var i in id_list) {
                            var details = this.history[id_list[i] + "_" + this.config[current].src];
                            if (details) {
                                result.values.push(details);
                            } else {
                                Galaxy.emit.debug("ui-select-content::value()", "Requested details not found for '" + id_list[i] + "'.");
                                return null;
                            }
                        }
                        result.values.sort(function(a, b) {
                            return a.hid - b.hid;
                        });
                        return result;
                    }
                }
            } else {
                Galaxy.emit.debug("ui-select-content::value()", "Invalid value/source '" + new_value + "'.");
            }
            return null;
        },

        /** Change of current select field */
        _changeCurrent: function _changeCurrent() {
            var self = this;
            _.each(this.fields, function(field, i) {
                if (self.model.get("current") == i) {
                    field.$el.show();
                    _.each(self.$batch, function($batchfield, batchmode) {
                        $batchfield[self.config[i].batch == batchmode ? "show" : "hide"]();
                    });
                    self.button_type.value(i);
                } else {
                    field.$el.hide();
                }
            });
        },

        /** Change of type */
        _changeType: function _changeType() {
            var self = this;

            // identify selector type identifier i.e. [ flavor ]_[ type ]_[ multiple ]
            var config_id = (this.model.get("flavor") ? this.model.get("flavor") + "_" : "") + String(this.model.get("type")) + (this.model.get("multiple") ? "_multiple" : "");
            if (Configurations[config_id]) {
                this.config = Configurations[config_id];
            } else {
                this.config = Configurations["data"];
                Galaxy.emit.debug("ui-select-content::_changeType()", "Invalid configuration/type id '" + config_id + "'.");
            }

            // prepare extension component of error message
            var data = self.model.get("data");
            var extensions = _utils2.default.textify(this.model.get("extensions"));
            var src_labels = this.model.get("src_labels");

            // build views
            this.fields = [];
            this.button_data = [];
            _.each(this.config, function(c, i) {
                self.button_data.push({
                    value: i,
                    icon: c.icon,
                    tooltip: c.tooltip
                });
                self.fields.push(new _uiSelectDefault2.default.View({
                    optional: self.model.get("optional"),
                    multiple: c.multiple,
                    searchable: !c.multiple || data && data[c.src] && data[c.src].length > self.model.get("pagelimit"),
                    individual: true,
                    error_text: "No " + (extensions ? extensions + " " : "") + (src_labels[c.src] || "content") + " available.",
                    onchange: function onchange() {
                        self.trigger("change");
                    }
                }));
            });
            this.button_type = new _uiMisc2.default.RadioButton.View({
                value: this.model.get("current"),
                data: this.button_data,
                onchange: function onchange(value) {
                    self.model.set("current", value);
                    self.trigger("change");
                }
            });

            // append views
            this.$el.empty();
            var button_width = 0;
            if (this.fields.length > 1) {
                this.$el.append(this.button_type.$el);
                button_width = Math.max(0, this.fields.length * 36) + "px";
            }
            _.each(this.fields, function(field) {
                self.$el.append(field.$el.css({
                    "margin-left": button_width
                }));
            });
            _.each(this.$batch, function($batchfield, batchmode) {
                self.$el.append($batchfield.css({
                    "margin-left": button_width
                }));
            });
            this.model.set("current", 0);
            this._changeCurrent();
            this._changeData();
        },

        /** Change of wait flag */
        _changeWait: function _changeWait() {
            var self = this;
            _.each(this.fields, function(field) {
                field[self.model.get("wait") ? "wait" : "unwait"]();
            });
        },

        /** Change of available options */
        _changeData: function _changeData() {
            var options = this.model.get("data");
            var self = this;
            var select_options = {};
            _.each(options, function(items, src) {
                select_options[src] = [];
                _.each(items, function(item) {
                    select_options[src].push({
                        hid: item.hid,
                        keep: item.keep,
                        label: item.hid + ": " + item.name,
                        value: item.id,
                        tags: item.tags
                    });
                    self.history[item.id + "_" + src] = item;
                });
            });
            _.each(this.config, function(c, i) {
                select_options[c.src] && self.fields[i].add(select_options[c.src], function(a, b) {
                    return b.hid - a.hid;
                });
            });
        },

        /** Change of incoming value */
        _changeValue: function _changeValue() {
            var new_value = this.model.get("value");
            if (new_value && new_value.values && new_value.values.length > 0) {
                // create list with content ids
                var list = [];
                _.each(new_value.values, function(value) {
                    list.push(value.id);
                });
                // sniff first suitable field type from config list
                var src = new_value.values[0].src;
                var multiple = new_value.values.length > 1;
                for (var i = 0; i < this.config.length; i++) {
                    var field = this.fields[i];
                    var c = this.config[i];
                    if (c.src == src && [multiple, true].indexOf(c.multiple) !== -1) {
                        this.model.set("current", i);
                        field.value(list);
                        break;
                    }
                }
            } else {
                _.each(this.fields, function(field) {
                    field.value(null);
                });
            }
        },

        /** Handles drop events e.g. from history panel */
        _handleDrop: function _handleDrop(ev) {
            try {
                var data = this.model.get("data");
                var current = this.model.get("current");
                var config = this.config[current];
                var field = this.fields[current];
                var drop_data = JSON.parse(ev.originalEvent.dataTransfer.getData("text"))[0];
                var new_id = drop_data.id;
                var new_src = drop_data.history_content_type == "dataset" ? "hda" : "hdca";
                var new_value = {
                    id: new_id,
                    src: new_src
                };
                if (data && _.findWhere(data[new_src], new_value)) {
                    if (config.src == new_src) {
                        var current_value = field.value();
                        if (current_value && config.multiple) {
                            if (current_value.indexOf(new_id) == -1) {
                                current_value.push(new_id);
                            }
                        } else {
                            current_value = new_id;
                        }
                        field.value(current_value);
                    } else {
                        this.model.set("value", {
                            values: [new_value]
                        });
                        this.model.trigger("change:value");
                    }
                    this.trigger("change");
                    this._handleDropStatus("success");
                } else {
                    this._handleDropStatus("danger");
                }
            } catch (e) {
                this._handleDropStatus("danger");
            }
            ev.preventDefault();
        },

        /** Highlight drag result */
        _handleDropStatus: function _handleDropStatus(status) {
            var self = this;
            this.$el.removeClass("ui-dragover").addClass("ui-dragover-" + status);
            setTimeout(function() {
                self.$el.removeClass("ui-dragover-" + status);
            }, this.model.get("statustimer"));
        },

        /** Assists in identifying the batch mode */
        _batch: function _batch(result) {
            result["batch"] = false;
            var current = this.model.get("current");
            var config = this.config[current];
            if (config.src == "hdca" && !config.multiple) {
                var hdca = this.history[this.fields[current].value() + "_hdca"];
                if (hdca && hdca.map_over_type) {
                    result["batch"] = true;
                }
            }
            if (config.batch == Batch.LINKED || config.batch == Batch.ENABLED) {
                result["batch"] = true;
                if (config.batch == Batch.ENABLED && this.button_product.value() === "true") {
                    result["product"] = true;
                }
            }
            return result;
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-select-content.js.map
