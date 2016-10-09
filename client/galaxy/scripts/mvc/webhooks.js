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
            if (webhook.activate) {
                this.$el.html('<div id="' + webhook.name + '"></div>');
                if (webhook.styles) $('<style/>', {type: 'text/css'}).text(webhook.styles).appendTo('head');
                if (webhook.script) $('<script/>', {type: 'text/javascript'}).text(webhook.script).appendTo('head');
            }
            return this;
        }
    });

    var addToMastheadMenu = function() {
        var webhooks = new Webhooks();
        webhooks.url = Galaxy.root + 'api/webhooks/masthead/all';
        webhooks.fetch({
            success: function() {
                $(document).ready(function() {
                    $.each(webhooks.models, function(index, model) {
                        var webhook = model.toJSON();
                        if (webhook.activate) {
                            Galaxy.page.masthead.collection.add({
                                id      : webhook.name,
                                icon    : (typeof webhook.config.icon != 'undefined') ? webhook.config.icon : '',
                                url     : (typeof webhook.config.url != 'undefined') ? webhook.config.url : '',
                                tooltip : (typeof webhook.config.tooltip != 'undefined') ? webhook.config.tooltip : '',
                                onclick : (typeof webhook.config.function != 'undefined') ? new Function(webhook.config.function) : '',
                                // visible : webhook.activate
                            });
                        }
                    });
                });
            }
        });
    };

    var addToHistoryMenu = function(_l, menu) {
        var webhooks = new Webhooks();
        webhooks.url = Galaxy.root + 'api/webhooks/history-menu/all';
        webhooks.fetch({
            async: false,   // slows down History Panel loading
            success: function() {
                var webhooks_menu = [];

                $.each(webhooks.models, function(index, model) {
                    var webhook = model.toJSON();
                    if (webhook.activate) {
                        webhooks_menu.push({
                            html : _l( webhook.config.title ),
                            // func: function() {},
                            anon : true
                        });
                    }
                });

                if (webhooks_menu.length > 0) {
                    webhooks_menu.unshift({
                        html   : _l( 'Webhooks' ),
                        header : true
                    });
                    $.merge(menu, webhooks_menu);
                }
            }
        });
    };

    return {
        Webhooks: Webhooks,
        WebhookView: WebhookView,
        addToMastheadMenu: addToMastheadMenu,
        addToHistoryMenu: addToHistoryMenu
    };
});
