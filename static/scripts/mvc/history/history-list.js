define("mvc/history/history-list", ["exports", "utils/localization", "utils/utils", "mvc/grid/grid-view", "mvc/history/history-model", "mvc/history/copy-dialog"], function(exports, _localization, _utils, _gridView, _historyModel, _copyDialog) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _gridView2 = _interopRequireDefault(_gridView);

    var _historyModel2 = _interopRequireDefault(_historyModel);

    var _copyDialog2 = _interopRequireDefault(_copyDialog);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** This class renders the grid list. */
    var HistoryGridView = _gridView2.default.extend({
        _showCopyDialog: function _showCopyDialog(id) {
            var history = new _historyModel2.default.History({
                id: id
            });
            history.fetch().fail(function() {
                alert("History could not be fetched. Please contact an administrator");
            }).done(function() {
                (0, _copyDialog2.default)(history, {}).done(function() {
                    if (window.parent && window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel) {
                        window.parent.Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                    window.location.reload(true);
                });
            });
        },
        /** Add an operation to the items menu */
        _add_operation: function _add_operation(popup, operation, item) {
            var self = this;
            var settings = item.operation_config[operation.label];
            if (operation.label == "Copy") {
                operation.onclick = function(id) {
                    self._showCopyDialog(id);
                };
            }
            if (settings.allowed && operation.allow_popup) {
                popup.addItem({
                    html: operation.label,
                    href: settings.url_args,
                    target: settings.target,
                    confirmation_text: operation.confirm,
                    func: function func(e) {
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
        title: (0, _localization2.default)("Histories"),
        initialize: function initialize(options) {
            var self = this;
            this.setElement($("<div/>"));
            this.model = new Backbone.Model();
            _utils2.default.get({
                url: Galaxy.root + "history/" + options.action_id + "?" + $.param(Galaxy.params),
                success: function success(response) {
                    response.dict_format = true;
                    self.model.set(response);
                    self.render();
                }
            });
        },

        render: function render() {
            var grid = new HistoryGridView(this.model.attributes);
            this.$el.empty().append(grid.$el);
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/history/history-list.js.map
