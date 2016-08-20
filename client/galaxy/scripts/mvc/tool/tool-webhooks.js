/**
  Webhooks
**/
define([], function() {
    var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

    var WebhookModel = Backbone.Model.extend({
        urlRoot:  galaxyRoot + 'api/webhooks/toolview',
        defaults: {
            name: '',
            type: '',
            styles: '',
            script: ''
        }
    });

    var WebhookView = Backbone.View.extend({
        el: '#webhook-toolview',

        initialize: function() {
            var me = this;
            this.model = new WebhookModel;
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
        WebhookView: WebhookView
    };
});
