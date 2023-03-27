import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import Select from "mvc/ui/ui-select-default";
import { getGalaxyInstance } from "app";

/** Batch mode variations */
const Batch = { DISABLED: "disabled", ENABLED: "enabled", LINKED: "linked" };

/** List of available content selectors options */
const Configurations = {
    data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            library: true,
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.LINKED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.LINKED,
        },
    ],
    data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collections"),
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    module_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
    module_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder",
            tooltip: _l("Multiple collections"),
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
};

/** View for hda and dce content selector ui elements */
const View = Backbone.View.extend({
    initialize: function (options) {
        const self = this;
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                src_labels: { hda: "dataset", hdca: "dataset collection" },
                pagelimit: 100,
                statustimer: 1000,
            }).set(options);
        this.setElement($("<div/>").addClass("ui-select-content"));
        this.button_product = new Ui.RadioButton.View({
            value: "false",
            data: [
                {
                    icon: "fa fa-chain",
                    value: "false",
                    tooltip:
                        "Linked inputs will be run in matched order with other datasets e.g. use this for matching forward and reverse reads.",
                },
                {
                    icon: "fa fa-chain-broken",
                    value: "true",
                    tooltip: "Unlinked dataset inputs will be run against *all* other inputs.",
                },
            ],
        });
        this.$batch = {
            linked: $(this._templateBatch()).clone(),
            enabled: $(this._templateBatch()).clone().append(this.button_product.$el),
        };

        // add drag-drop event handlers
        const element = this.$el.get(0);
        element.addEventListener("dragenter", (e) => {
            this.lastenter = e.target;
            self.$el.addClass("ui-dragover");
        });
        element.addEventListener("dragover", (e) => {
            e.preventDefault();
        });
        element.addEventListener("dragleave", (e) => {
            this.lastenter === e.target && self.$el.removeClass("ui-dragover");
        });
        element.addEventListener("drop", (e) => {
            e.preventDefault();
            try {
                const drop_data = JSON.parse(e.dataTransfer.getData("text"))[0];
                this._handleDropValues(drop_data);
            } catch (e) {
                this._handleDropStatus("danger");
            }
        });

        // track current cache elements
        this.cache = {};

        // add listeners
        this.listenTo(this.model, "change:data", this._changeData, this);
        this.listenTo(this.model, "change:wait", this._changeWait, this);
        this.listenTo(this.model, "change:current", this._changeCurrent, this);
        this.listenTo(this.model, "change:value", this._changeValue, this);
        this.listenTo(
            this.model,
            "change:type change:optional change:multiple change:extensions",
            this._changeType,
            this
        );
        this.render();

        // add change event
        this.on("change", () => {
            options.onchange && options.onchange(self.value());
        });
    },

    render: function () {
        this._changeType();
        this._changeValue();
        this._changeWait();
    },

    /** Indicate that select fields are being updated */
    wait: function () {
        this.model.set("wait", true);
    },

    /** Indicate that the options update has been completed */
    unwait: function () {
        this.model.set("wait", false);
    },

    /** Update data representing selectable options */
    update: function (input_def) {
        this.model.set("data", input_def.options);
    },

    /** Return the currently selected dataset values */
    value: function (new_value) {
        if (new_value) {
            this._patchValue(new_value);
            this.model.set("value", new_value);
        }
        const current = this.model.get("current");
        if (this.config[current]) {
            let id_list = this.fields[current].value();
            if (id_list !== null) {
                id_list = Array.isArray(id_list) ? id_list : [id_list];
                if (id_list.length > 0) {
                    const result = this._batch({ values: [] });
                    for (const i in id_list) {
                        const details = this.cache[`${id_list[i]}_${this.config[current].src}`];
                        if (details) {
                            const unpatchedValue = this._unpatchValue(details);
                            result.values.push(unpatchedValue);
                        } else {
                            console.debug(
                                "ui-select-content::value()",
                                `Requested details not found for '${id_list[i]}'.`
                            );
                            return null;
                        }
                    }
                    result.values.sort((a, b) => a.hid - b.hid);
                    return result;
                }
            }
        } else {
            console.debug("ui-select-content::value()", `Invalid value/source '${new_value}'.`);
        }
        return null;
    },

    /** Change of current select field */
    _changeCurrent: function () {
        _.each(this.fields, (field, i) => {
            const cnf = this.config[i];
            if (this.model.get("current") == i) {
                field.$el.show();
                _.each(this.$batch, ($batchfield, batchmode) => {
                    if (cnf.batch == batchmode) {
                        $batchfield.show();
                    } else {
                        $batchfield.hide();
                    }
                });
                if (cnf.src == "hda") {
                    this.button_dialog.show();
                    this.upload_dialog.show();
                } else {
                    this.button_dialog.hide();
                    this.upload_dialog.hide();
                }
                this.button_type.value(i);
            } else {
                field.$el.hide();
            }
        });
        if (this.fields.length > 1) {
            this.button_type.show();
        } else {
            this.button_type.hide();
        }
    },

    /** Change of type */
    _changeType: function () {
        const self = this;
        const galaxy = getGalaxyInstance();

        // identify selector type identifier i.e. [ flavor ]_[ type ]_[ multiple ]
        const config_id =
            (this.model.get("flavor") ? `${this.model.get("flavor")}_` : "") +
            String(this.model.get("type")) +
            (this.model.get("multiple") ? "_multiple" : "");
        if (Configurations[config_id]) {
            this.config = Configurations[config_id];
        } else {
            this.config = Configurations["data"];
            console.debug("ui-select-content::_changeType()", `Invalid configuration/type id '${config_id}'.`);
        }

        // prepare extension component of error message
        const data = self.model.get("data");
        const formats = this.model.get("extensions");
        const extensions = Utils.textify(formats);
        const src_labels = this.model.get("src_labels");

        // build radio button for data selectors
        this.fields = [];
        this.button_data = [];
        _.each(this.config, (c, i) => {
            self.button_data.push({
                value: i,
                icon: c.icon,
                tooltip: c.tooltip,
            });
            self.fields.push(
                new Select.View({
                    optional: self.model.get("optional"),
                    multiple: c.multiple,
                    searchable:
                        !c.multiple || (data && data[c.src] && data[c.src].length > self.model.get("pagelimit")),
                    individual: true,
                    error_text: `No ${extensions ? `${extensions} ` : ""}${src_labels[c.src] || "content"} available.`,
                    onchange: function () {
                        self.trigger("change");
                    },
                })
            );
        });
        this.button_type = new Ui.RadioButton.View({
            value: this.model.get("current"),
            data: this.button_data,
            cls: "pr-lg-2",
            onchange: function (value) {
                self.model.set("current", value);
                self.trigger("change");
            },
        });

        // build data dialog button
        this.button_dialog = new Ui.Button({
            icon: "fa-folder-open-o",
            tooltip: "Browse Datasets",
            onclick: () => {
                const current = this.model.get("current");
                const cnf = this.config[current];
                galaxy.data.dialog(
                    (response) => {
                        this._handleDropValues(response, false);
                    },
                    {
                        multiple: cnf.multiple,
                        library: !!cnf.library,
                        format: null,
                        allowUpload: true,
                    }
                );
            },
        });

        // build data dialog button
        this.upload_dialog = new Ui.Button({
            icon: "fa-upload",
            tooltip: "Upload Dataset",
            onclick: () => {
                const current = this.model.get("current");
                const cnf = this.config[current];
                // model doesn't have format yet unfortunately, need to get through to here.
                galaxy.data.dialog(
                    (response) => {
                        this._handleDropValues(response, false);
                    },
                    {
                        multiple: cnf.multiple,
                        formats: formats,
                        new: true,
                    }
                );
            },
        });

        // append views
        const $fields = $("<div/>").addClass("overflow-auto w-100 py-2 py-lg-0 pr-lg-2 ");
        this.$el
            .empty()
            .addClass("d-flex flex-row flex-wrap flex-lg-nowrap")
            .append($("<div/>").append(this.button_type.$el))
            .append($fields);
        if (galaxy.config.upload_from_form_button == "always-on") {
            this.$el.append($("<div style='margin-right: 5px;' />").append(this.upload_dialog.$el));
        }
        this.$el.append($("<div/>").append(this.button_dialog.$el));
        _.each(this.fields, (field) => {
            $fields.append(field.$el);
        });
        _.each(this.$batch, ($batchfield, batchmode) => {
            $fields.append($batchfield);
        });
        this.model.set("current", 0);
        this._changeCurrent();
        this._changeData();
    },

    /** Change of wait flag */
    _changeWait: function () {
        const self = this;
        _.each(this.fields, (field) => {
            field[self.model.get("wait") ? "wait" : "unwait"]();
        });
    },

    /** Change of available options */
    _changeData: function () {
        const options = this.model.get("data");
        const self = this;
        const select_options = { hda: [], hdca: [] };
        _.each(options, (items, src) => {
            _.each(items, (item) => {
                self._patchValue(item);
                const current_src = item.src || src;
                const addOption = !this.model.attributes.tag || item.tags.includes(this.model.attributes.tag);
                if (addOption) {
                    select_options[current_src].push({
                        hid: item.hid,
                        keep: item.keep,
                        label: `${item.hid || "Selected"}: ${item.name}`,
                        value: item.id,
                        origin: item.origin,
                        tags: item.tags,
                    });
                }
                self.cache[`${item.id}_${current_src}`] = item;
            });
        });
        _.each(this.config, (c, i) => {
            select_options[c.src] && self.fields[i].add(select_options[c.src], (a, b) => b.hid - a.hid);
        });
    },

    /** Change of incoming value */
    _changeValue: function () {
        const new_value = this.model.get("value");
        if (new_value && new_value.values && new_value.values.length > 0) {
            // create list with content ids
            const list = [];
            _.each(new_value.values, (value) => {
                list.push(value.id);
            });
            // sniff first suitable field type from config list
            const src = new_value.values[0].src;
            const multiple = new_value.values.length > 1;
            for (let i = 0; i < this.config.length; i++) {
                const field = this.fields[i];
                const c = this.config[i];
                if (c.src == src && [multiple, true].indexOf(c.multiple) !== -1) {
                    this.model.set("current", i);
                    field.value(list);
                    break;
                }
            }
        } else {
            _.each(this.fields, (field) => {
                field.value(null);
            });
        }
    },

    /** Source helper matches history_content_types to source types */
    _getSource: function (v) {
        return v.history_content_type == "dataset_collection" ? "hdca" : "hda";
    },

    /** Library datasets are displayed and selected together with history datasets,
        Dataset collection elements are displayed together with history dataset collections **/
    _patchValue: function (v) {
        const patchTo = { ldda: "hda", dce: "hdca" };
        if (v.values) {
            _.each(v.values, (v) => {
                this._patchValue(v);
            });
        } else if (patchTo[v.src]) {
            v.origin = v.src;
            v.src = patchTo[v.src];
            v.id = `${v.origin}${v.id}`;
        }
    },

    /** Restores original value e.g. after patching library datasets **/
    _unpatchValue: function (v) {
        if (v.origin) {
            const d = Object.assign({}, v);
            d.id = d.id.substr(d.origin.length);
            d.src = d.origin;
            return d;
        }
        return v;
    },

    /** Add values from drag/drop */
    _handleDropValues: function (drop_data, drop_partial = true) {
        const self = this;
        const data = this.model.get("data");
        const current = this.model.get("current");
        const config = this.config[current];
        const field = this.fields[current];
        if (data) {
            const values = Array.isArray(drop_data) ? drop_data : [drop_data];
            if (values.length > 0) {
                let data_changed = false;
                _.each(values, (v) => {
                    // element_id deals with override in old backbone code,
                    // can remove when old history is deprecated
                    v.id = v.element_id || v.id;
                    self._patchValue(v);
                    const new_id = v.id;
                    const new_src = (v.src = this._getSource(v));
                    const new_value = { id: new_id, src: new_src };
                    if (!_.findWhere(data[new_src], new_value)) {
                        data_changed = true;
                        data[new_src].push({
                            id: new_id,
                            src: new_src,
                            hid: v.hid || "Selected",
                            name: v.name ? v.name : new_id,
                            origin: v.origin,
                            keep: true,
                            tags: [],
                        });
                    }
                });
                if (data_changed) {
                    this._changeData();
                }
                const first_id = values[0].id;
                const first_src = values[0].src;
                if (config.src == first_src && drop_partial) {
                    let current_value = field.value();
                    if (current_value && config.multiple) {
                        _.each(values, (v) => {
                            if (current_value.indexOf(v.id) == -1) {
                                current_value.push(v.id);
                            }
                        });
                    } else {
                        current_value = first_id;
                    }
                    field.value(current_value);
                } else {
                    this.model.set("value", { values: values });
                    this.model.trigger("change:value");
                }
                this.trigger("change");
            }
        }
        this._handleDropStatus("success");
    },

    /** Highlight drag result */
    _handleDropStatus: function (status) {
        const self = this;
        this.$el.removeClass("ui-dragover").addClass(`ui-dragover-${status}`);
        setTimeout(() => {
            self.$el.removeClass(`ui-dragover-${status}`);
        }, this.model.get("statustimer"));
    },

    /** Assists in identifying the batch mode */
    _batch: function (result) {
        result["batch"] = false;
        const current = this.model.get("current");
        const config = this.config[current];
        if (config.src == "dce" || config.src == "hdca") {
            const element = this.cache[`${this.fields[current].value()}_${config.src}`];
            if (element && element.map_over_type) {
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
    },

    /** Template for batch mode execution options */
    _templateBatch: function () {
        return `<div class="form-text text-muted" style="clear: both;">
                    <i class="fa fa-sitemap"/>
                    <span>
                        This is a batch mode input field. Separate jobs will be triggered for each dataset selection.
                    </span>
                </div>`;
    },
});

export default {
    View: View,
};
