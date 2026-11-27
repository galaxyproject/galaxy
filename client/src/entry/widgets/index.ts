import "@/compat-config";
import "@/style/scss/base.scss";

import { createPinia } from "pinia";
import { createApp, ref } from "vue";

import { initGalaxyInstance } from "@/app";
import { embedKey } from "@/composables/embed";
import { installAppPlugins } from "@/utils/mountVueComponent";
import { onDomReady } from "@/utils/onDomReady";

import { getRouter } from "./router";

import App from "./App.vue";

onDomReady(async () => {
    await initGalaxyInstance();
    const app = createApp(App);
    app.provide(embedKey, ref(true));
    app.use(getRouter());
    app.use(createPinia());
    installAppPlugins(app);
    app.mount("#app");
});
