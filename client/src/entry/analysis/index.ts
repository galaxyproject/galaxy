// index.ts
import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { initGalaxyInstance } from "@/app";
import { initSentry } from "@/app/addons/sentry";
import { initWebhooks } from "@/app/addons/webhooks";

import { getRouter } from "./router";

import App from "./App.vue";

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
