import { standardInit, addInitialization } from "onload";

import Vue from "vue";
import App from "./App.vue";
import store from "store";
import { getRouter } from "./router";

addInitialization((Galaxy) => {
    console.log("App setup");
    new Vue({
        el: "body",
        render: (h) => h(App),
        router: getRouter(Galaxy),
        store: store,
    });
});

window.addEventListener("load", () => standardInit("app"));
