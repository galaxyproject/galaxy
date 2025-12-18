import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

let webhookData = undefined;

async function getWebhookData() {
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

export async function loadWebhooks(type) {
    const webhooks = await getWebhookData();
    if (type) {
        return webhooks.filter((item) => item.type && item.type.indexOf(type) !== -1);
    } else {
        return webhooks;
    }
}

export function pickWebhook(data) {
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
