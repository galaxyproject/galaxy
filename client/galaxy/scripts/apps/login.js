import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import Page from "layout/page";
import Login from "components/login/Login.vue";
import Password from "components/login/Password.vue";
import Vue from "vue";
import { setGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";

window.app = function app(options, bootstrapped) {
    console.debug("Analysis init");

    let Galaxy = setGalaxyInstance(GalaxyApp => {
        let galaxy = new GalaxyApp(options, bootstrapped);
        galaxy.debug("login app");
        return galaxy;
    });

    $(() => {
        Galaxy.page = new Page.View(options);
        var vm = document.createElement("div");
        Galaxy.display(vm);
        var component = Galaxy.params.token || Galaxy.params.expired_user ? Password : Login;
        var loginInstance = Vue.extend(component);
        new loginInstance({propsData: options}).$mount(vm);
    });
};
