/**
  Webhooks
**/
define([], function() {
    var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

    var MastheadWebhookModel = Backbone.Model.extend({
        urlRoot: galaxyRoot + 'api/webhooks/masthead',
        defaults: {
            visible: true
        }
    });

    var ToolWebhookModel = Backbone.Model.extend({
        urlRoot:  galaxyRoot + 'api/webhooks/tools'
    });

    var MastheadWebhookView = Backbone.View.extend({
        initialize: function() {
            var me = this;
            this.model = new MastheadWebhookModel;
            this.model.fetch({
                success: function() {
                    me.render();
                }
            });
        },

        render: function() {
            var webhook = this.model.toJSON();

            // There must be a better way to make sure Galaxy is fully loaded
            $(document).ready(function() {
                if (webhook.visible) {
                    Galaxy.page.masthead.collection.add({
                        id      : webhook.name,
                        icon    : (typeof webhook.config.icon != 'undefined') ? webhook.config.icon : '',
                        url     : (typeof webhook.config.url != 'undefined') ? webhook.config.url : '',
                        tooltip : (typeof webhook.config.tooltip != 'undefined') ? webhook.config.tooltip : '',
                        // visible : webhook.visible
                    });
                }
            });
            return this;
        }
    });

    var ToolWebhookView = Backbone.View.extend({
        el: '#webhook-tools',

        initialize: function() {
            var me = this;
            this.model = new ToolWebhookModel;
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

    return {
        MastheadWebhookView: MastheadWebhookView,
        ToolWebhookView: ToolWebhookView
    };
});
