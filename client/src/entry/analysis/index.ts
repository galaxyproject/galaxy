import Vue, { provide } from "vue";
import { PiniaVuePlugin, createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import App from "./App.vue";
import { getRouter } from "./router";
import { addInitialization, standardInit } from "@/onload";
import store from "@/store";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

addInitialization((Galaxy: any) => {
    console.log("App setup");
    const router = getRouter(Galaxy);
    new Vue({
        el: "#app",
        setup() {
            provide("store", store);
        },
        render: (h) => h(App),
        router: router,
        store: store,
        pinia: pinia,
    });
});

window.addEventListener("load", () => standardInit("app"));
