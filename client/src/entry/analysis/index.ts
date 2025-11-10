// index.ts
import { createPinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

import { standardInit } from "@/onload";

import { getRouter } from "./router";

import App from "./App.vue";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

window.addEventListener("load", async () => {
    const galaxy = (await standardInit("app")) as any;
    console.log("App setup");

    const router = getRouter(galaxy);
    galaxy.router = router;

    new Vue({
        el: "#app",
        render: (h) => h(App),
        router,
        pinia,
    });
});
