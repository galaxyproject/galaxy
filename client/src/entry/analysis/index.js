import { standardInit, addInitialization } from "onload";

import Vue from "vue";
import App from "./App.vue";
import store from "store";
import { getRouter } from "./router";

addInitialization((Galaxy) => {
    console.log("App setup");
    const router = getRouter(Galaxy);
    new Vue({
        el: "#app",
        render: (h) => h(App),
        router: router,
        store: store,
    });
    Galaxy.router = router;
});

window.addEventListener("load", () => standardInit("app"));
