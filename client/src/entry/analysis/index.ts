import { createPinia } from "pinia";
import { configureCompat, createApp } from "@vue/compat";

import { addInitialization, standardInit } from "@/onload";

import { getRouter } from "./router";

import App from "./App.vue";

// Configure compat mode
configureCompat({
    MODE: 2,
});

const pinia = createPinia();

addInitialization((Galaxy: any) => {
    console.log("App setup");
    const router = getRouter(Galaxy);
    // When initializing the primary app we bind the routing back to Galaxy for
    // external use (e.g. gtn webhook) -- longer term we discussed plans to
    // parameterize webhooks and initialize them explicitly with state.
    Galaxy.router = router;
    const app = createApp(App);
    app.use(router);
    app.use(pinia);
    app.mount("#app");
});

window.addEventListener("load", () => standardInit("app"));
