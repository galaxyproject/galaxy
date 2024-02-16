import axios from "axios";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";

import { rethrowSimple } from "@/utils/simple-error";

let webhookData = undefined;

async function getWebHookData() {
    if (webhookData === undefined) {
        try {
            const { data } = await axios.get(`${getAppRoot()}api/webhooks`);
            webhookData = data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    return webhookData;
}

const WebhookView = Backbone.View.extend({
    el: "#webhook-view",

    initialize: function (options) {
        const toolId = options.toolId || "";
        const toolVersion = options.toolVersion || "";

        this.$el.attr("tool_id", toolId);
        this.$el.attr("tool_version", toolVersion);

        getWebHookData().then((data) => {
            const filteredData = filterData(data, options);
            if (filteredData.length > 0) {
                this.render(weightedRandomPick(filteredData));
            }
        });
    },

    render: function (model) {
        this.$el.html(`<div id="${model.id}"></div>`);
        Utils.appendScriptStyle(model);
        return this;
    },
});

function filterData(data, options) {
    let filteredData = data;
    if (options.type) {
        filteredData = filterType(data, options.type);
    }
    return filteredData;
}

const load = (options) => {
    getWebHookData().then((data) => {
        options.callback(filterData(data, options));
    });
};

function filterType(data, type) {
    return data.filter((item) => {
        const itype = item.type;
        if (itype) {
            return itype.indexOf(type) !== -1;
        } else {
            return false;
        }
    });
}

function weightedRandomPick(data) {
    const weights = data.map((d) => d.weight);
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
