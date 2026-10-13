import "@/compat-config";
import "@/style/scss/base.scss";

import { createPinia } from "pinia";
import { createApp } from "vue";

import { initGalaxyInstance } from "@/app";
import { installAppPlugins } from "@/utils/mountVueComponent";

import { getRouter } from "./router";

import App from "./App.vue";

window.addEventListener("load", async () => {
    await initGalaxyInstance();
    const app = createApp(App);
    app.use(getRouter());
    app.use(createPinia());
    installAppPlugins(app);
    app.mount("#app");
});
