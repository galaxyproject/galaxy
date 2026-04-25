// index.ts
import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { installPendingRequestsInterceptor } from "@/api/pendingRequests";
import { initGalaxyInstance } from "@/app";
import { initSentry } from "@/app/addons/sentry";
import { initWebhooks } from "@/app/addons/webhooks";

import { getRouter } from "./router";

import App from "./App.vue";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

// Attach the shared AbortController signal to every outgoing axios request
// so we can cancel in-flight anonymous-cookie requests before login/register
// navigates — otherwise their late ``Set-Cookie: galaxysession=<anon>`` can
// clobber the authenticated cookie.
installPendingRequestsInterceptor();

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
