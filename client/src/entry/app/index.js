import Vue from "vue";
import App from "./App.vue";
import { standardInit, addInitialization } from "onload";

addInitialization((Galaxy, { options = {} }) => {
    console.log("App setup");
    new Vue({
        el: "body",
        render: (h) => h(App),
    });
});

window.addEventListener("load", () => standardInit("app"));
