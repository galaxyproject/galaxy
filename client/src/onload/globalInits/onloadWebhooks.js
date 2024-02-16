import Utils from "utils/utils";
import Webhooks from "utils/webhooks";

export function onloadWebhooks(Galaxy) {
    if (Galaxy.config.enable_webhooks) {
        Webhooks.load({
            type: "onload",
            callback: function (webhooks) {
                webhooks.forEach((webhook) => {
                    if (webhook.activate && webhook.script) {
                        Utils.appendScriptStyle(webhook);
                    }
                });
            },
        });
    }
}
