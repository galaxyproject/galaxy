/**
  Webhooks
**/
define([], function() {
    var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

    var MenuWebhookModel = Backbone.Model.extend({
        urlRoot: galaxyRoot + 'api/webhooks/topbar'
    });

    var ToolWebhookModel = Backbone.Model.extend({
        urlRoot:  galaxyRoot + 'api/webhooks/toolview'
    });

    var MenuWebhookView = Backbone.View.extend({
        initialize: function() {
            var me = this;
            this.model = new MenuWebhookModel;
            this.model.fetch({
                success: function() {
                    me.render();
                }
            });
        },

        render: function() {
            var webhook = this.model.toJSON();;

            // There must be a better way to make sure Galaxy is fully loaded
            $(document).ready(function() {
                if (webhook.visible) {
                    Galaxy.page.masthead.collection.add({
                        id      : webhook.name,
                        icon    : webhook.icon,
                        url     : webhook.url,
                        tooltip : webhook.tooltip,
                        // visible : webhook.visible
                    });
                }
            });
            return this;
        }
    });

    var ToolWebhookView = Backbone.View.extend({
        el: '#webhook-toolview',

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
        MenuWebhookView: MenuWebhookView,
        ToolWebhookView: ToolWebhookView
    };
});
