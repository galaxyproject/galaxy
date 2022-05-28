import { standardInit, addInitialization } from "onload";

import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "store";

addInitialization((Galaxy, { options = {} }) => {
    console.log("App setup");
    new Vue({
        el: "body",
        render: (h) => h(App),
        router: router,
        store: store,
    });
    router.push("workflows/edit");
});

window.addEventListener("load", () => standardInit("app"));
