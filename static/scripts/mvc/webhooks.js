define("mvc/webhooks", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    /**
      Webhooks
    **/

    var WebhookModel = Backbone.Model.extend({
        defaults: {
            activate: false
        }
    });

    var Webhooks = Backbone.Collection.extend({
        model: WebhookModel
    });

    var WebhookView = Backbone.View.extend({
        el: "#webhook-view",

        initialize: function initialize(options) {
            var me = this;
            var toolId = options.toolId || "";
            var toolVersion = options.toolVersion || "";

            this.$el.attr("tool_id", toolId);
            this.$el.attr("tool_version", toolVersion);

            this.model = new WebhookModel();
            this.model.urlRoot = options.urlRoot;
            this.model.fetch({
                success: function success() {
                    me.render();
                }
            });
        },

        render: function render() {
            var webhook = this.model.toJSON();

            this.$el.html("<div id=\"" + webhook.name + "\"></div>");
            if (webhook.styles) $("<style/>", {
                type: "text/css"
            }).text(webhook.styles).appendTo("head");
            if (webhook.script) $("<script/>", {
                type: "text/javascript"
            }).text(webhook.script).appendTo("head");

            return this;
        }
    });

    var add = function add(options) {
        var webhooks = new Webhooks();

        webhooks.url = Galaxy.root + options.url;
        webhooks.fetch({
            async: options.async ? options.async : true,
            success: options.callback
        });
    };

    exports.default = {
        Webhooks: Webhooks,
        WebhookView: WebhookView,
        add: add
    };
});
//# sourceMappingURL=../../maps/mvc/webhooks.js.map
