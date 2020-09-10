import Webhooks from "mvc/webhooks";
import Utils from "utils/utils";

export function loadWebhookMenuItems(items) {
    Webhooks.load({
        type: "masthead",
        callback: function (webhooks) {
            webhooks.each((model) => {
                const webhook = model.toJSON();
                if (webhook.activate) {
                    const obj = {
                        id: webhook.id,
                        icon: webhook.config.icon,
                        url: webhook.config.url,
                        tooltip: webhook.config.tooltip,
                        /*jslint evil: true */
                        onclick: webhook.config.function && new Function(webhook.config.function),
                        visible: true,
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
