import _l from "utils/localization";
/** This class renders the grid list. */
import Utils from "utils/utils";
import GridView from "mvc/grid/grid-view";
import HistoryModel from "mvc/history/history-model";
import historyCopyDialog from "mvc/history/copy-dialog";

var HistoryGridView = GridView.extend({
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
        this.setElement($("<div/>"));
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
