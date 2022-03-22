/** This class renders the grid list. */
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import AjaxQueue from "utils/ajax-queue";
import Utils from "utils/utils";
import GridView from "mvc/grid/grid-view";
import { History } from "mvc/history/history-model";
import historyCopyDialog from "mvc/history/copy-dialog";
import LoadingIndicator from "ui/loading-indicator";

var HistoryGridView = GridView.extend({
    initialize: function (grid_config) {
        this.ajaxQueue = new AjaxQueue.AjaxQueue();
        GridView.prototype.initialize.call(this, grid_config);
    },

    init_grid_elements: function () {
        const ajaxQueue = this.ajaxQueue;
        ajaxQueue.stop();
        GridView.prototype.init_grid_elements.call(this);
        const fetchDetails = $.makeArray(
            this.$el.find(".delayed-value-datasets_by_state").map((i, el) => {
                return () => {
                    const historyId = $(el).data("id");
                    const url = `${getAppRoot()}api/histories/${historyId}?keys=nice_size,contents_active,contents_states`;
                    const options = {};
                    options.url = url;
                    options.type = "GET";
                    options.success = (req) => {
                        const contentsStates = req.contents_states;
                        let stateHtml = "";
                        for (const state of ["ok", "running", "queued", "new", "error"]) {
                            const stateCount = contentsStates[state];
                            if (stateCount) {
                                stateHtml += `<div class="count-box state-color-${state}" title="Datasets in ${state} state">${stateCount}</div> `;
                            }
                        }
                        const contentsActive = req.contents_active;
                        const deleted = contentsActive.deleted;
                        if (deleted) {
                            stateHtml += `<div class="count-box state-color-deleted" title="Deleted datasets">${deleted}</div> `;
                        }
                        const hidden = contentsActive.hidden;
                        if (hidden) {
                            stateHtml += `<div class="count-box state-color-hidden" title="Hidden datasets">${hidden}</div> `;
                        }
                        $(`.delayed-value-datasets_by_state[data-id='${historyId}']`).html(stateHtml);
                        $(`.delayed-value-disk_size[data-id='${historyId}']`).html(req.nice_size);
                    };
                    return $.ajax(options);
                };
            })
        );
        fetchDetails.forEach((fn) => ajaxQueue.add(fn));
        ajaxQueue.start();
    },
    _showCopyDialog: function (id) {
        var history = new History({ id: id });
        history
            .fetch()
            .fail(() => {
                alert("History could not be fetched. Please contact an administrator");
            })
            .done(() => {
                historyCopyDialog(history, {}).done(() => {
                    const Galaxy = getGalaxyInstance();
                    if (Galaxy && Galaxy.currHistoryPanel) {
                        Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                    window.location.reload(true);
                });
            });
    },
    /** Add an operation to the items menu */
    add_operation: function (popup, operation, item) {
        if (operation.label == "Copy") {
            operation.onclick = (id) => {
                this._showCopyDialog(id);
            };
        }
        GridView.prototype.add_operation.call(this, popup, operation, item);
    },
});

var View = Backbone.View.extend({
    title: _l("Histories"),
    initialize: function (options) {
        const Galaxy = getGalaxyInstance();
        LoadingIndicator.markViewAsLoading(this);

        if (options.action_id == "list_published") {
            this.active_tab = "shared";
        } else if (options.action_id == "list") {
            this.active_tab = "user";
        }
        this.model = new Backbone.Model();
        Utils.get({
            url: `${getAppRoot()}history/${options.action_id}?${$.param(Galaxy.params)}`,
            success: (response) => {
                this.model.set(response);
                this.render();
            },
        });
    },

    render: function () {
        var grid = new HistoryGridView(this.model.attributes);
        this.$el.empty().append(grid.$el);
    },
});

export default {
    View: View,
};
