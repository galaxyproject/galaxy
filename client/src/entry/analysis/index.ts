import { createPinia } from "pinia";
import { configureCompat, createApp } from "@vue/compat";

import { initGalaxyInstance } from "@/app";
import { initSentry } from "@/app/addons/sentry";
import { initWebhooks } from "@/app/addons/webhooks";

import { getRouter } from "./router";

import App from "./App.vue";

// Configure compat mode
configureCompat({
    MODE: 2,
    GLOBAL_SET: true,  // Enable Vue.set for libraries that need it
    GLOBAL_DELETE: true,  // Enable Vue.delete for libraries that need it
});

const pinia = createPinia();

window.addEventListener("load", async () => {
    // Create Galaxy object
    const Galaxy = await initGalaxyInstance();

    // Build router
    const router = getRouter(Galaxy);

    // Initialize globals
    await initSentry(Galaxy, router);
    await initWebhooks(Galaxy);

    // When initializing the primary app we bind the routing back to Galaxy for
    // external use (e.g. gtn webhook) -- longer term we discussed plans to
    // parameterize webhooks and initialize them explicitly with state.
    Galaxy.router = router;

    // Mount application with Vue 3 createApp
    const app = createApp(App);
    app.use(router);
    app.use(pinia);
    app.mount("#app");
});
