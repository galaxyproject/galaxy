/** Frame manager uses the window manager to create the scratch book masthead icon and functionality **/
import _ from "underscore";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { createTabularDatasetChunkedView, TabularDataset } from "mvc/dataset/data";
import _l from "utils/localization";
import WinBox from "winbox/src/js/winbox.js";
import "winbox/dist/css/winbox.min.css";
import { urlData } from "utils/url";

export default Backbone.View.extend({
    initialize: function (options) {
        options = options || {};
        this.setElement("<div />");
        this.counter = 0;
        this.active = false;
        this.buttonActive = {
            id: "enable-scratchbook",
            icon: "fa-th",
            tooltip: _l("Enable/Disable Scratchbook"),
            toggle: false,
            onclick: () => {
                this.active = !this.active;
                this.buttonActive.toggle = this.active;
                this.buttonActive.show_note = this.active;
                this.buttonActive.note_cls = this.active && "fa fa-check";
                if (!this.active) {
                    this.$el.hide();
                }
            },
        };
        this.buttonLoad = {
            id: "show-scratchbook",
            icon: "fa-eye",
            tooltip: _l("Show/Hide Scratchbook"),
            show_note: true,
            visible: false,
            note: "",
            onclick: (e) => {
                if (this.visible) {
                    this.$el.hide();
                } else {
                    this.$el.show();
                }
            },
        };
        this.history_cache = {};
    },

    getFrames() {
        // needed for Vue.js integration
        return this;
    },

    beforeUnload() {
        let confirmText = "";
        if (this.counter > 0) {
            confirmText = `You opened ${this.counter} frame(s) which will be lost.`;
        }
        return confirmText;
    },

    /** Add a dataset */
    addDataset: function (dataset_id) {
        const self = this;
        let current_dataset = null;
        const Galaxy = getGalaxyInstance();
        if (Galaxy && Galaxy.currHistoryPanel) {
            const history_id = Galaxy.currHistoryPanel.model.id;
            this.history_cache[history_id] = {
                name: Galaxy.currHistoryPanel.model.get("name"),
                dataset_ids: [],
            };
            Galaxy.currHistoryPanel.collection.each((model) => {
                if (!model.get("deleted") && model.get("visible") && model.get("history_content_type") == "dataset") {
                    self.history_cache[history_id].dataset_ids.push(model.get("id"));
                }
            });
        }
        const _findDataset = (dataset, offset) => {
            if (dataset) {
                const history_details = self.history_cache[dataset.get("history_id")];
                if (history_details && history_details.dataset_ids) {
                    const dataset_list = history_details.dataset_ids;
                    const pos = dataset_list.indexOf(dataset.get("id"));
                    if (pos !== -1 && pos + offset >= 0 && pos + offset < dataset_list.length) {
                        return dataset_list[pos + offset];
                    }
                }
            }
        };
        const _loadOffset = (dataset, offset, frame) => {
            const new_dataset_id = _findDataset(dataset, offset);
            if (new_dataset_id) {
                self._loadDataset(new_dataset_id, (new_dataset, config) => {
                    current_dataset = new_dataset;
                    frame.model.set(config);
                });
            }
        };
        this._loadDataset(dataset_id, (dataset, config) => {
            current_dataset = dataset;
            self.add(
                _.extend(
                    {
                        menu: [
                            {
                                icon: "fa fa-chevron-circle-left",
                                tooltip: _l("Previous in History"),
                                onclick: function (frame) {
                                    _loadOffset(current_dataset, -1, frame);
                                },
                                disabled: function () {
                                    return !_findDataset(current_dataset, -1);
                                },
                            },
                            {
                                icon: "fa fa-chevron-circle-right",
                                tooltip: _l("Next in History"),
                                onclick: function (frame) {
                                    _loadOffset(current_dataset, 1, frame);
                                },
                                disabled: function () {
                                    return !_findDataset(current_dataset, 1);
                                },
                            },
                        ],
                    },
                    config
                )
            );
        });
    },

    _loadDataset: function (dataset_id, callback) {
        const url = `api/datasets/${dataset_id}`;
        urlData({ url }).then((dataset) => {
            const is_tabular = _.find(
                ["tabular", "interval"],
                (data_type) => dataset.data_type.indexOf(data_type) !== -1
            );
            const history_details = this.history_cache[dataset.history_id];
            const title = history_details ? `${history_details.name}: ${dataset.name}` : dataset.name;
            callback(
                dataset,
                is_tabular
                    ? {
                          title: title,
                          url: null,
                          content: createTabularDatasetChunkedView({
                              model: new TabularDataset(dataset.toJSON()),
                              embedded: true,
                              height: "100%",
                          }).$el,
                      }
                    : {
                          title: title,
                          url: `${getAppRoot()}datasets/${dataset_id}/display/?preview=True`,
                          content: null,
                      }
            );
        });
    },

    /** Add and display a new frame/window based on options. */
    add: function (options) {
        if (options.target == "_blank") {
            window.open(options.url);
        } else if (options.target == "_top" || options.target == "_parent" || options.target == "_self") {
            window.location = options.url;
        } else if (!this.active || options.noscratchbook) {
            const $galaxy_main = $(window.parent.document).find("#galaxy_main");
            if (options.target == "galaxy_main" || options.target == "center") {
                if ($galaxy_main.length === 0) {
                    window.location = this._build_url(options.url, { use_panels: true });
                } else {
                    $galaxy_main.attr("src", options.url);
                }
            } else {
                window.location = options.url;
            }
        } else {
            options.url = this._build_url(options.url, { hide_panels: true, hide_masthead: true });
            options.class = "modern";
            WinBox.new(options);
        }
    },

    /** Url helper */
    _build_url: function (url, options) {
        if (url) {
            url += url.indexOf("?") == -1 ? "?" : "&";
            Object.entries(options).forEach(([key, value]) => {
                url += `${key}=${value}&`;
            });
            return url;
        }
    },
});
