import { standardInit, addInitialization } from "onload";

import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "store";

addInitialization(() => {
    console.log("App setup");
    new Vue({
        el: "body",
        render: (h) => h(App),
        router: router,
        store: store,
    });
});

window.addEventListener("load", () => standardInit("app"));
