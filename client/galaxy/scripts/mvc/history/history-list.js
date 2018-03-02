import _l from "utils/localization";
import AjaxQueue from "utils/ajax-queue";
import Utils from "utils/utils";
/** This class renders the grid list. */
import GridView from "mvc/grid/grid-view";
import HistoryModel from "mvc/history/history-model";
import historyCopyDialog from "mvc/history/copy-dialog";
import LoadingIndicator from "ui/loading-indicator";

var HistoryGridView = GridView.extend({
    initialize: function(grid_config) {
        this.ajaxQueue = new AjaxQueue.AjaxQueue();
        GridView.prototype.initialize.call(this, grid_config);
    },

    init_grid_elements: function() {
        const ajaxQueue = this.ajaxQueue;
        ajaxQueue.stop();
        GridView.prototype.init_grid_elements.call(this);
        const fetchDetails = $.makeArray(
            this.$el.find(".delayed-value-datasets_by_state").map((i, el) => {
                return () => {
                    const historyId = $(el).data("history-id");
                    const url = `${
                        Galaxy.root
                    }api/histories/${historyId}?keys=nice_size,contents_active,contents_states`;
                    const options = {};
                    options.url = url;
                    options.type = "GET";
                    options.success = req => {
                        const contentsStates = req["contents_states"];
                        let stateHtml = "";
                        for (let state of ["ok", "running", "queued", "new", "error"]) {
                            const stateCount = contentsStates[state];
                            if (stateCount) {
                                stateHtml += `<div class="count-box state-color-${state}" title="Datasets in ${state} state">${stateCount}</div> `;
                            }
                        }
                        const contentsActive = req["contents_active"];
                        const deleted = contentsActive["deleted"];
                        if (deleted) {
                            stateHtml += `<div class="count-box state-color-deleted" title="Deleted datasets">${deleted}</div> `;
                        }
                        const hidden = contentsActive["hidden"];
                        if (hidden) {
                            stateHtml += `<div class="count-box state-color-hidden" title="Hidden datasets">${hidden}</div> `;
                        }
                        $(`.delayed-value-datasets_by_state[data-history-id='${historyId}']`).html(stateHtml);
                        $(`.delayed-value-disk_size[data-history-id='${historyId}']`).html(req["nice_size"]);
                    };
                    var xhr = jQuery.ajax(options);
                    return xhr;
                };
            })
        );
        fetchDetails.forEach(fn => ajaxQueue.add(fn));
        ajaxQueue.start();
    },
    _showCopyDialog: function(id) {
        var history = new HistoryModel.History({ id: id });
        history
            .fetch()
            .fail(() => {
                alert("History could not be fetched. Please contact an administrator");
            })
            .done(() => {
                historyCopyDialog(history, {}).done(() => {
                    if (window.parent && window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel) {
                        window.parent.Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                    window.location.reload(true);
                });
            });
    },
    /** Add an operation to the items menu */
    _add_operation: function(popup, operation, item) {
        var self = this;
        var settings = item.operation_config[operation.label];
        if (operation.label == "Copy") {
            operation.onclick = id => {
                self._showCopyDialog(id);
            };
        }
        if (settings.allowed && operation.allow_popup) {
            popup.addItem({
                html: operation.label,
                href: settings.url_args,
                target: settings.target,
                confirmation_text: operation.confirm,
                func: function(e) {
                    e.preventDefault();
                    var label = $(e.target).html();
                    if (operation.onclick) {
                        operation.onclick(item.encode_id);
                    } else {
                        self.execute(this.findItemByHtml(label));
                    }
                }
            });
        }
    }
});

var View = Backbone.View.extend({
    title: _l("Histories"),
    initialize: function(options) {
        var self = this;
        LoadingIndicator.markViewAsLoading(this);

        this.model = new Backbone.Model();
        Utils.get({
            url: `${Galaxy.root}history/${options.action_id}?${$.param(Galaxy.params)}`,
            success: function(response) {
                self.model.set(response);
                self.render();
            }
        });
    },

    render: function() {
        var grid = new HistoryGridView(this.model.attributes);
        this.$el.empty().append(grid.$el);
    }
});

export default {
    View: View
};
