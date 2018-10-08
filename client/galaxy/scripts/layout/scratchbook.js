/** Frame manager uses the ui-frames to create the scratch book masthead icon and functionality **/
import * as Backbone from "backbone";
import * as _ from "underscore";
import Frames from "mvc/ui/ui-frames";
import { Dataset, createTabularDatasetChunkedView, TabularDataset } from "mvc/dataset/data";
import visualization from "viz/visualization";
import { TracksterUI } from "viz/trackster";
import _l from "utils/localization";

/* global Galaxy */
/* global $ */

export default Backbone.View.extend({
    initialize: function(options) {
        var self = this;
        options = options || {};
        this.frames = new Frames.View({ visible: false });
        this.setElement(this.frames.$el);
        this.buttonActive = options.collection.add({
            id: "enable-scratchbook",
            icon: "fa-th",
            tooltip: _l("Enable/Disable Scratchbook"),
            onclick: function() {
                self.active = !self.active;
                self.buttonActive.set({
                    toggle: self.active,
                    show_note: self.active,
                    note_cls: self.active && "fa fa-check"
                });
                if (!self.active) {
                    self.frames.hide();
                }
            },
            onbeforeunload: function() {
                if (self.frames.length() > 0) {
                    return `You opened ${self.frames.length()} frame(s) which will be lost.`;
                }
            }
        });
        this.buttonLoad = options.collection.add({
            id: "show-scratchbook",
            icon: "fa-eye",
            tooltip: _l("Show/Hide Scratchbook"),
            show_note: true,
            visible: false,
            onclick: function(e) {
                if (self.frames.visible) {
                    self.frames.hide();
                } else {
                    self.frames.show();
                }
            }
        });
        this.frames
            .on("add remove", function() {
                if (this.visible && this.length() === 0) {
                    this.hide();
                }
                self.buttonLoad.set({
                    note: this.length(),
                    visible: this.length() > 0
                });
            })
            .on("show hide ", function() {
                self.buttonLoad.set({
                    toggle: this.visible,
                    icon: (this.visible && "fa-eye") || "fa-eye-slash"
                });
            });
        this.history_cache = {};
    },

    /** Add a dataset to the frames */
    addDataset: function(dataset_id) {
        var self = this;
        var current_dataset = null;
        if (Galaxy && Galaxy.currHistoryPanel) {
            var history_id = Galaxy.currHistoryPanel.collection.historyId;
            this.history_cache[history_id] = {
                name: Galaxy.currHistoryPanel.model.get("name"),
                dataset_ids: []
            };
            Galaxy.currHistoryPanel.collection.each(model => {
                if (!model.get("deleted") && model.get("visible")) {
                    self.history_cache[history_id].dataset_ids.push(model.get("id"));
                }
            });
        }
        var _findDataset = (dataset, offset) => {
            if (dataset) {
                var history_details = self.history_cache[dataset.get("history_id")];
                if (history_details && history_details.dataset_ids) {
                    var dataset_list = history_details.dataset_ids;
                    var pos = dataset_list.indexOf(dataset.get("id"));
                    if (pos !== -1 && pos + offset >= 0 && pos + offset < dataset_list.length) {
                        return dataset_list[pos + offset];
                    }
                }
            }
        };
        var _loadDatasetOffset = (dataset, offset, frame) => {
            var new_dataset_id = _findDataset(dataset, offset);
            if (new_dataset_id) {
                self._loadDataset(new_dataset_id, (new_dataset, config) => {
                    current_dataset = new_dataset;
                    frame.model.set(config);
                });
            } else {
                frame.model.trigger("change");
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
                                onclick: function(frame) {
                                    _loadDatasetOffset(current_dataset, -1, frame);
                                },
                                disabled: function() {
                                    return !_findDataset(current_dataset, -1);
                                }
                            },
                            {
                                icon: "fa fa-chevron-circle-right",
                                tooltip: _l("Next in History"),
                                onclick: function(frame) {
                                    _loadDatasetOffset(current_dataset, 1, frame);
                                },
                                disabled: function() {
                                    return !_findDataset(current_dataset, 1);
                                }
                            }
                        ]
                    },
                    config
                )
            );
        });
    },

    _loadDataset: function(dataset_id, callback) {
        var self = this;
        var dataset = new Dataset({ id: dataset_id });
        $.when(dataset.fetch()).then(() => {
            var is_tabular = _.find(
                ["tabular", "interval"],
                data_type => dataset.get("data_type").indexOf(data_type) !== -1
            );
            var title = dataset.get("name");
            var history_details = self.history_cache[dataset.get("history_id")];
            if (history_details) {
                title = `${history_details.name}: ${title}`;
            }
            callback(
                dataset,
                is_tabular
                    ? {
                          title: title,
                          url: null,
                          content: createTabularDatasetChunkedView({
                              model: new TabularDataset(dataset.toJSON()),
                              embedded: true,
                              height: "100%"
                          }).$el
                      }
                    : {
                          title: title,
                          url: `${Galaxy.root}datasets/${dataset_id}/display/?preview=True`,
                          content: null
                      }
            );
        });
    },

    /** Add a trackster visualization to the frames. */
    addTrackster: function(viz_id) {
        var self = this;
        var viz = new visualization.Visualization({ id: viz_id });
        $.when(viz.fetch()).then(() => {
            var ui = new TracksterUI(Galaxy.root);

            // Construct frame config based on dataset's type.
            var frame_config = {
                title: viz.get("name"),
                type: "other",
                content: function(parent_elt) {
                    // Create view config.
                    var view_config = {
                        container: parent_elt,
                        name: viz.get("title"),
                        id: viz.id,
                        // FIXME: this will not work with custom builds b/c the dbkey needed to be encoded.
                        dbkey: viz.get("dbkey"),
                        stand_alone: false
                    };

                    var latest_revision = viz.get("latest_revision");
                    var drawables = latest_revision.config.view.drawables;

                    // Set up datasets in drawables.
                    _.each(drawables, d => {
                        d.dataset = {
                            hda_ldda: d.hda_ldda,
                            id: d.dataset_id
                        };
                    });
                    ui.create_visualization(
                        view_config,
                        latest_revision.config.viewport,
                        latest_revision.config.view.drawables,
                        latest_revision.config.bookmarks,
                        false
                    );
                }
            };
            self.add(frame_config);
        });
    },

    /** Add and display a new frame/window based on options. */
    add: function(options) {
        if (options.target == "_blank") {
            window.open(options.url);
        } else if (options.target == "_top" || options.target == "_parent" || options.target == "_self") {
            window.location = options.url;
        } else if (!this.active || options.noscratchbook) {
            var $galaxy_main = $(window.parent.document).find("#galaxy_main");
            if (options.target == "galaxy_main" || options.target == "center") {
                if ($galaxy_main.length === 0) {
                    window.location = this._build_url(options.url, { use_panels: true });
                } else {
                    $galaxy_main.attr("src", options.url);
                }
            } else window.location = options.url;
        } else {
            options.url = this._build_url(options.url, { hide_panels: true, hide_masthead: true });
            this.frames.add(options);
        }
    },

    /** Url helper */
    _build_url: function(url, options) {
        if (url) {
            url += url.indexOf("?") == -1 ? "?" : "&";
            url += $.param(options, true);
            return url;
        }
    }
});
