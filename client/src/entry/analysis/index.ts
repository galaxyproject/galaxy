// index.ts
import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { initGalaxyInstance } from "@/app";
import { initSentry } from "@/app/addons/sentry";
import { initWebhooks } from "@/app/addons/webhooks";
import * as bundleEntries from "@/bundleEntries";
import * as config from "@/onload/loadConfig";

import { getRouter } from "./router";

import App from "./App.vue";

// Expose bundleEntries and config to window for Mako templates
// These were previously in libs.js but moved here to avoid circular deps with Vite
declare global {
    interface Window {
        bundleEntries: typeof bundleEntries;
        config: typeof config & { _queue?: unknown[][]; _processQueue?: (fn: typeof config.set) => void };
    }
}

// Process any queued config.set() calls from the stub (used in Vite dev mode)
// The stub is injected by vite-plugin-galaxy-dev-server.js to handle the race
// condition where inline scripts call config.set() before this module loads
if (window.config?._processQueue) {
    window.config._processQueue(config.set);
}

window.bundleEntries = bundleEntries;
window.config = config;

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

window.addEventListener("load", async () => {
    // Create Galaxy object
    const Galaxy = await initGalaxyInstance();

    // Build router
    const router = getRouter(Galaxy);

    // Initialize globals
    await initSentry(Galaxy, router);
    await initWebhooks(Galaxy);

    // Mount application
    new Vue({
        el: "#app",
        render: (h) => h(App),
        router,
        pinia,
    });
});
