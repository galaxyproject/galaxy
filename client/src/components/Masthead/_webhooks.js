import Utils from "utils/utils";
import Webhooks from "utils/webhooks";

export function loadWebhookMenuItems(items) {
    Webhooks.load({
        type: "masthead",
        callback: function (webhooks) {
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
                    Utils.appendScriptStyle(webhook);
                }
            });
        },
    });
}
