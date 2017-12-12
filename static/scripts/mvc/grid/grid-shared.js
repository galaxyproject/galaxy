define("mvc/grid/grid-shared", ["exports", "mvc/grid/grid-view"], function(exports, _gridView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _gridView2 = _interopRequireDefault(_gridView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.setElement($("<div/>"));
            this.model = new Backbone.Model(options);
            this.item = this.model.get("item");
            this.title = this.model.get("plural");
            $.ajax({
                url: Galaxy.root + this.item + "/" + this.model.get("action_id") + "?" + $.param(Galaxy.params),
                success: function success(response) {
                    response["dict_format"] = true;
                    self.model.set(response);
                    self.render();
                }
            });
        },

        render: function render() {
            var grid = new _gridView2.default(this.model.attributes);
            this.$el.empty().append(grid.$el);
            this.$el.append(this._templateShared());
        },

        _templateShared: function _templateShared() {
            var self = this;
            var $tmpl = $("<div><h2>" + this.model.get("plural") + " shared with you by others</h2></div>");
            var options = this.model.attributes;
            if (options.shared_by_others && options.shared_by_others.length > 0) {
                var $table = $('<table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">' + '<tr class="header">' + "<th>Title</th>" + "<th>Owner</th>" + "</tr>" + "</table>");
                _.each(options.shared_by_others, function(it, index) {
                    var display_url = Galaxy.root + self.item + "/display_by_username_and_slug?username=" + it.username + "&slug=" + it.slug;
                    $table.append("<tr><td><a href=\"" + display_url + "\">" + _.escape(it.title) + "</a></td><td>" + _.escape(it.username) + "</td></tr>");
                });
                $tmpl.append($table);
            } else {
                $tmpl.append("No " + this.model.get("plural").toLowerCase() + " have been shared with you.");
            }
            return $tmpl;
        }
    }); /** This class renders the grid list with shared section. */
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/grid/grid-shared.js.map
