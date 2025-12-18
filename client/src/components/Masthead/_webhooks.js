import { appendScriptStyle } from "@/utils/utils";
import { loadWebhooks } from "@/utils/webhooks";

export async function loadMastheadWebhooks(items) {
    const webhooks = await loadWebhooks("masthead");
    webhooks.forEach((webhook) => {
        if (webhook.activate) {
            const obj = {
                id: webhook.id,
                icon: webhook.config.icon,
                url: webhook.config.url,
                tooltip: webhook.config.tooltip,
                /*jslint evil: true */
                onclick: webhook.config.function && new Function(webhook.config.function),
                target: "_parent",
            };
            items.push(obj);
            // Append masthead script and styles to Galaxy main
            appendScriptStyle(webhook);
        }
    });
}
