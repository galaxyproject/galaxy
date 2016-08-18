/**
  Webhooks
**/
define([], function() {
    var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

    var WebhookModel = Backbone.Model.extend({
        urlRoot:  galaxyRoot + 'api/webhooks/toolview',
        defaults: {
            name: '',
            path: ''
        }
    });

    var WebhookView = Backbone.View.extend({
        el: '#webhook-toolview',
        webhookTemplate: _.template('<p>name: <%= name %><br>path: <%= path %></p>'),

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
            var webhookContent = this.model.toJSON();
            if (webhookContent.css_styles) $('<style/>').text(webhookContent.css_styles).appendTo('head');
            this.$el.html(this.webhookTemplate(webhookContent));
            return this;
        }
    });

    return {
        WebhookView: WebhookView
    };
});
