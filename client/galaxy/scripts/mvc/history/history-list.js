/** This class renders the grid list. */
import Utils from "utils/utils";
import GridView from "mvc/grid/grid-view";
import HistoryModel from "mvc/history/history-model";
import historyCopyDialog from "mvc/history/copy-dialog";
var View = Backbone.View.extend({
    title: "Histories",
    initialize: function(options) {
        var self = this;
        this.setElement($("<div/>"));
        this.model = new Backbone.Model();
        Utils.get({
            url: `${Galaxy.root}history/${options.action_id}?${$.param(Galaxy.params)}`,
            success: function(response) {
                response["dict_format"] = true;
                _.each(response["operations"], operation => {
                    if (operation.label == "Copy") {
                        operation.onclick = id => {
                            self._showCopyDialog(id);
                        };
                    }
                });
                self.model.set(response);
                self.render();
            }
        });
    },

    render: function() {
        var grid = new GridView(this.model.attributes);
        this.$el.empty().append(grid.$el);
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
    }
});

export default {
    View: View
};
