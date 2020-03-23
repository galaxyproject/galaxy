import Webhooks from "mvc/webhooks";
import Utils from "utils/utils";

export function onloadWebhooks(Galaxy) {
    console.log("onloadWebhooks");

    if (Galaxy.config.enable_webhooks) {
        Webhooks.load({
            type: "onload",
            callback: function (webhooks) {
                webhooks.each((model) => {
                    var webhook = model.toJSON();
                    if (webhook.activate && webhook.script) {
                        Utils.appendScriptStyle(webhook);
                    }
                });
            },
        });
    }
}
