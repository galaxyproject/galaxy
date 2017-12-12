define("mvc/lazy/lazy-limited", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.default = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.$container = options.$container;
            this.collection = options.collection;
            this.new_content = options.new_content;
            this.max = options.max || 50;
            this.content_list = {};
            this.$message = $("<div/>").addClass("ui-limitloader").append("...only the first " + this.max + " entries are visible.");
            this.$container.append(this.$message);
            this.listenTo(this.collection, "reset", this._reset, this);
            this.listenTo(this.collection, "add", this._refresh, this);
            this.listenTo(this.collection, "remove", this._remove, this);
        },

        /** Checks if the limit has been reached */
        _done: function _done() {
            var done = _.size(this.content_list) > this.max;
            this.$message[done ? "show" : "hide"]();
            return done;
        },

        /** Remove all content */
        _reset: function _reset() {
            _.each(this.content_list, function(content) {
                content.remove();
            });
            this.content_list = {};
            this.$message.hide();
        },

        /** Remove content */
        _remove: function _remove(model) {
            var model_id = model.id;
            var content = this.content_list[model_id];
            if (content) {
                content.remove();
                delete this.content_list[model_id];
            }
            this._refresh();
        },

        /** Refreshes container content by adding new views if visible */
        _refresh: function _refresh() {
            if (!this._done()) {
                for (var i in this.collection.models) {
                    var model = this.collection.models[i];
                    var view = this.content_list[model.id];
                    if (!this.content_list[model.id]) {
                        var content = this.new_content(model);
                        this.content_list[model.id] = content;
                        if (this._done()) {
                            break;
                        }
                    }
                }
            }
        }
    });
});
//# sourceMappingURL=../../../maps/mvc/lazy/lazy-limited.js.map
