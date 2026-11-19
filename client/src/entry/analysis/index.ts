import "@/compat-config";
import "@galaxyproject/galaxy-ui/tokens.css";

import { createPinia } from "pinia";
import { createApp } from "vue";

import { installPendingRequestsInterceptor } from "@/api/pendingRequests";
import { installStaleCacheRetryInterceptor } from "@/api/staleCacheRetry";
import { initGalaxyInstance } from "@/app";
import { initSentry } from "@/app/addons/sentry";
import { initWebhooks } from "@/app/addons/webhooks";
import { installAppPlugins } from "@/utils/mountVueComponent";

import { getRouter } from "./router";

import App from "./App.vue";

const pinia = createPinia();

// Attach the shared AbortController signal to every outgoing axios request
// so we can cancel in-flight anonymous-cookie requests before login/register
// navigates — otherwise their late ``Set-Cookie: galaxysession=<anon>`` can
// clobber the authenticated cookie.
installPendingRequestsInterceptor();
installStaleCacheRetryInterceptor();

window.addEventListener("load", async () => {
    // Create Galaxy object
    const Galaxy = await initGalaxyInstance();

    // Build router
    const router = getRouter(Galaxy);
    // Expose the router on the Galaxy object for code outside Vue components,
    // such as webhooks (e.g. the GTN webhook).
    Galaxy.router = router;

    // Initialize globals
    await initWebhooks(Galaxy);

    // Mount application with Vue 3 createApp
    const app = createApp(App);
    app.use(router);
    app.use(pinia);
    installAppPlugins(app);
    initSentry(Galaxy, router, app);
    app.mount("#app");
});
