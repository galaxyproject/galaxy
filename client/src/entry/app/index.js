import Vue from "vue";
import App from "./App.vue";
import { standardInit, addInitialization } from "onload";
import store from "store";

addInitialization((Galaxy, { options = {} }) => {
    console.log("App setup");
    new Vue({
        el: "body",
        store: store,
        render: (h) => h(App),
    });
});

window.addEventListener("load", () => standardInit("app"));
