define([], function() {
    var WebhookModel = Backbone.Model.extend({
        defaults: {
            activate: !1
        }
    }), Webhooks = Backbone.Collection.extend({
        model: WebhookModel
    }), WebhookView = Backbone.View.extend({
        el: "#webhook-view",
        initialize: function(options) {
            var me = this;
            this.model = new WebhookModel(), this.model.urlRoot = options.urlRoot, this.model.fetch({
                success: function() {
                    me.render();
                }
            });
        },
        render: function() {
            var webhook = this.model.toJSON();
            return this.$el.html('<div id="' + webhook.name + '"></div>'), webhook.styles && $("<style/>", {
                type: "text/css"
            }).text(webhook.styles).appendTo("head"), webhook.script && $("<script/>", {
                type: "text/javascript"
            }).text(webhook.script).appendTo("head"), this;
        }
    }), add = function(options) {
        var webhooks = new Webhooks();
        webhooks.url = Galaxy.root + options.url, webhooks.fetch({
            async: "undefined" != typeof options.async ? options.async : !0,
            success: options.callback
        });
    };
    return {
        Webhooks: Webhooks,
        WebhookView: WebhookView,
        add: add
    };
});