/** Contains helpers to limit/lazy load views for backbone views */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";

export default Backbone.View.extend({
    initialize: function(options) {
        this.$container = options.$container;
        this.collection = options.collection;
        this.new_content = options.new_content;
        this.max = options.max || 50;
        this.content_list = {};
        this.$message = $("<div/>")
            .addClass("ui-limitloader")
            .append(`...only the first ${this.max} entries are visible.`)
            .hide();
        this.$container.append(this.$message);
        this.listenTo(this.collection, "reset", this._reset, this);
        this.listenTo(this.collection, "add", this._refresh, this);
        this.listenTo(this.collection, "remove", this._remove, this);
    },

    /** Checks if the limit has been reached */
    _done: function() {
        var done = _.size(this.content_list) > this.max;
        this.$message[done ? "show" : "hide"]();
        return done;
    },

    /** Remove all content */
    _reset: function() {
        _.each(this.content_list, content => {
            content.remove();
        });
        this.content_list = {};
        this.$message.hide();
    },

    /** Remove content */
    _remove: function(model) {
        var model_id = model.id;
        var content = this.content_list[model_id];
        if (content) {
            content.remove();
            delete this.content_list[model_id];
        }
        this._refresh();
    },

    /** Refreshes container content by adding new views if visible */
    _refresh: function() {
        if (!this._done()) {
            for (var i in this.collection.models) {
                var model = this.collection.models[i];
                // TODO: View is unused here.
                //var view = this.content_list[model.id];
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
