import Webhooks from "mvc/webhooks";
import Utils from "utils/utils";

/**
 * Initializes webhooks.
 *
 * @param {object} galaxy Galaxy application instance
 */
export const initWebhooks = (galaxy, config) => {
    console.log("initWebhooks");

    // NOTE: galaxy.config is not the same as the config we gave galaxy (it
    // applies its own defaults)
    if (galaxy.config.enable_webhooks) {
        Webhooks.load({
            type: "onload",
            callback: function(webhooks) {
                // This is tragic. We need to install a push server
                webhooks.each(model => {
                    var webhook = model.toJSON();
                    if (webhook.activate && webhook.script) {
                        Utils.appendScriptStyle(webhook);
                    }
                });
            }
        });
    }
};
