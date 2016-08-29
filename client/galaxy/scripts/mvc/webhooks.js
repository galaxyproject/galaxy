/**
  Webhooks
**/
define([], function() {

    var WebhookView = Backbone.View.extend({
        el: '#webhook-view',

        initialize: function(options) {
            var me = this;

            var WebhookModel = Backbone.Model.extend({
                urlRoot: options.urlRoot,
                defaults: {
                    activate: true
                }
            });

            this.model = new WebhookModel();
            this.model.fetch({
                success: function() {
                    me.render();
                }
            });
        },

        render: function() {
            var webhook = this.model.toJSON();

            if (webhook.activate) {
                if (webhook.type == 'masthead') {
                    // There must be a better way to make sure Galaxy is fully loaded
                    // $(document).ready(function() {
                    //     Galaxy.page.masthead.collection.add({
                    //         id      : webhook.name,
                    //         icon    : (typeof webhook.config.icon != 'undefined') ? webhook.config.icon : '',
                    //         url     : (typeof webhook.config.url != 'undefined') ? webhook.config.url : '',
                    //         tooltip : (typeof webhook.config.tooltip != 'undefined') ? webhook.config.tooltip : '',
                    //         // visible : webhook.activate
                    //     });
                    // });
                }

                this.$el.html('<div id="' + webhook.name + '"></div>');
                if (webhook.styles) $('<style/>', {type: 'text/css'}).text(webhook.styles).appendTo('head');
                if (webhook.script) $('<script/>', {type: 'text/javascript'}).text(webhook.script).appendTo('head');
            }
            return this;
        }
    });

    return {
        WebhookView: WebhookView
    };
});
