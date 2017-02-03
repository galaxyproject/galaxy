/**
  Webhooks
**/
define([], function() {

    var WebhookModel = Backbone.Model.extend({
        defaults: {
            activate: false
        }
    });

    var Webhooks = Backbone.Collection.extend({
        model: WebhookModel
    });

    var WebhookView = Backbone.View.extend({
        el: '#webhook-view',

        initialize: function(options) {
            var me = this;

            this.model = new WebhookModel();
            this.model.urlRoot = options.urlRoot;
            this.model.fetch({
                success: function() {
                    me.render();
                }
            });
        },

        render: function() {
            var webhook = this.model.toJSON();

            this.$el.html('<div id="' + webhook.name + '"></div>');
            if (webhook.styles) $('<style/>', {type: 'text/css'}).text(webhook.styles).appendTo('head');
            if (webhook.script) $('<script/>', {type: 'text/javascript'}).text(webhook.script).appendTo('head');
            
            return this;
        }
    });

    var add = function(options) {
        var webhooks = new Webhooks();

        webhooks.url = Galaxy.root + options.url;
        webhooks.fetch({
            async: (typeof options.async != 'undefined') ? options.async : true,
            success: options.callback
        });
    };

    return {
        Webhooks: Webhooks,
        WebhookView: WebhookView,
        add: add
    };
});
