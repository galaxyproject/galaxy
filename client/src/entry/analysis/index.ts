import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { addInitialization, standardInit } from "@/onload";

import { getRouter } from "./router";

import App from "./App.vue";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

addInitialization((Galaxy: any) => {
    console.log("App setup");
    const router = getRouter(Galaxy);
    // When initializing the primary app we bind the routing back to Galaxy for
    // external use (e.g. gtn webhook) -- longer term we discussed plans to
    // parameterize webhooks and initialize them explicitly with state.
    Galaxy.router = router;
    new Vue({
        el: "#app",
        render: (h) => h(App),
        router: router,
        pinia: pinia,
    });
});

window.addEventListener("load", () => standardInit("app"));
