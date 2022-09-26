import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";

const Webhooks = Backbone.Collection.extend({
    url: function () {
        return `${getAppRoot()}api/webhooks`;
    },
});

const WebhookView = Backbone.View.extend({
    el: "#webhook-view",

    initialize: function (options) {
        const toolId = options.toolId || "";
        const toolVersion = options.toolVersion || "";

        this.$el.attr("tool_id", toolId);
        this.$el.attr("tool_version", toolVersion);

        const webhooks = new Webhooks();
        webhooks.fetch({
            success: (data) => {
                if (options.type) {
                    data.reset(filterType(data, options.type));
                }
                if (data.length > 0) {
                    this.render(weightedRandomPick(data));
                }
            },
        });
    },

    render: function (model) {
        const webhook = model.toJSON();
        this.$el.html(`<div id="${webhook.id}"></div>`);
        Utils.appendScriptStyle(webhook);
        return this;
    },
});

const load = (options) => {
    const webhooks = new Webhooks();
    webhooks.fetch({
        async: options.async !== undefined ? options.async : true,
        success: (data) => {
            if (options.type) {
                data.reset(filterType(data, options.type));
            }
            options.callback(data);
        },
    });
};

function filterType(data, type) {
    return data.models.filter((item) => {
        const itype = item.get("type");
        if (itype) {
            return itype.indexOf(type) !== -1;
        } else {
            return false;
        }
    });
}

function weightedRandomPick(data) {
    const weights = data.pluck("weight");
    const sum = weights.reduce((a, b) => a + b);

    const normalizedWeightsMap = new Map();
    weights.forEach((weight, index) => {
        normalizedWeightsMap.set(index, parseFloat((weight / sum).toFixed(2)));
    });

    const table = [];
    for (const [index, weight] of normalizedWeightsMap) {
        for (let i = 0; i < weight * 100; i++) {
            table.push(index);
        }
    }

    return data.at(table[Math.floor(Math.random() * table.length)]);
}

export default {
    WebhookView: WebhookView,
    load: load,
};
