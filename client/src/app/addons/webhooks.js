import { appendScriptStyle } from "@/utils/utils";
import { loadWebhooks } from "@/utils/webhooks";

export async function initWebhooks(Galaxy) {
    if (Galaxy.config.enable_webhooks) {
        const webhooks = await loadWebhooks("onload");
        webhooks.forEach((webhook) => {
            if (webhook.activate && webhook.script) {
                appendScriptStyle(webhook);
            }
        });
    }
}
