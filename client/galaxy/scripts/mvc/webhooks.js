import Utils from 'utils/utils';

const Webhooks = Backbone.Collection.extend({
  url: `${Galaxy.root}api/webhooks`
});

const WebhookView = Backbone.View.extend({
  el: '#webhook-view',

  initialize: function (options) {
    const toolId = options.toolId || '';
    const toolVersion = options.toolVersion || '';

    this.$el.attr('tool_id', toolId);
    this.$el.attr('tool_version', toolVersion);

    const webhooks = new Webhooks();
    webhooks.fetch({
      success: data => {
        data.reset(filterType(data, options.type));

        if (data.length > 0) {
          const index = _.random(0, data.length - 1);
          this.render(data.at(index));
        }
      }
    });
  },

  render: function (model) {
    const webhook = model.toJSON();
    this.$el.html(`<div id="${webhook.id}"></div>`);
    Utils.appendScriptStyle(webhook);
    return this;
  }
});

const load = options => {
  const webhooks = new Webhooks();
  webhooks.fetch({
    async: options.async !== undefined ? options.async : true,
    success: data => {
      if (options.type) {
        data.reset(filterType(data, options.type));
      }
      options.callback(data);
    }
  });
};

function filterType (data, type) {
  return _.filter(data.models, item => item.get('type').indexOf(type) !== -1);
}

export default {
  WebhookView: WebhookView,
  load: load
};
