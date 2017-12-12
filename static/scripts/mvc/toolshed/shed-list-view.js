define("mvc/toolshed/shed-list-view", ["exports", "utils/localization", "mvc/toolshed/toolshed-model", "mvc/toolshed/util"], function(exports, _localization, _toolshedModel, _util) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _toolshedModel2 = _interopRequireDefault(_toolshedModel);

    var _util2 = _interopRequireDefault(_util);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = Backbone.View.extend({
        defaults: {
            tool_sheds: [{
                url: "https://toolshed.g2.bx.psu.edu/",
                name: "Galaxy Main Tool Shed"
            }]
        },

        initialize: function initialize(options) {
            var self = this;
            this.options = _.defaults(this.options || {}, this.defaults);
            this.model = new _toolshedModel2.default.ShedsCollection();
            this.listenTo(this.model, "sync", this.render);
            this.model.fetch();
        },

        el: "#center",

        render: function render(options) {
            this.options = _.defaults(this.options || {}, options, this.defaults);
            var toolshed_list_template = this.templateToolshedList;
            this.$el.html(toolshed_list_template({
                title: (0, _localization2.default)("Configured Galaxy Tool Sheds"),
                tool_sheds: this.model.models,
                queue: _util2.default.queueLength()
            }));
        },

        reDraw: function reDraw(options) {
            this.$el.empty();
            this.render(options);
        },

        templateToolshedList: _.template(['<div class="unified-panel-header" id="panel_header" unselectable="on">', '<div class="unified-panel-header-inner"><%= title %></div>', '<div class="unified-panel-header-inner" style="position: absolute; right: 5px; top: 0px;"><a href="#/queue">Repository Queue (<%= queue %>)</a></div>', "</div>", '<div class="unified-panel-body" id="list_toolsheds">', '<div class="form-row">', '<table class="grid">', "<% _.each(tool_sheds, function(shed) { %>", '<tr class="libraryTitle">', "<td>", '<div style="float: left; margin-left: 1px;" class="menubutton split">', '<a class="view-info shed-selector" href="#/categories/s/<%= shed.get("url") %>"><%= shed.get("name") %></a>', "</div>", "</td>", "</tr>", "<% }); %>", "</table>", "</div>", '<div style="clear: both"></div>', "</div>"].join(""))
    });

    exports.default = {
        ShedListView: View
    };
});
//# sourceMappingURL=../../../maps/mvc/toolshed/shed-list-view.js.map
