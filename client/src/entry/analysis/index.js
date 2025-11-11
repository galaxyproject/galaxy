// index.ts
import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { standardInit } from "@/onload";
import { initSentry } from "@/onload/globalInits/initSentry";
import { onloadWebhooks } from "@/onload/globalInits/onloadWebhooks";

import { getRouter } from "./router";

import App from "./App.vue";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

window.addEventListener("load", async () => {
    // Create Galaxy object
    const Galaxy = await standardInit("app");

    // Build router
    const router = getRouter(Galaxy);

    // Initialize globals
    await initSentry(Galaxy);
    await onloadWebhooks(Galaxy);

    // Mount application
    new Vue({
        el: "#app",
        render: (h) => h(App),
        router,
        pinia,
    });
});
