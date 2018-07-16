import jQuery from "jquery";
var $ = jQuery;
import GalaxyApp from "galaxy";
import Page from "layout/page";
import Login from "components/login/Login.vue";
import Password from "components/login/Password.vue";
import Vue from "vue";

window.app = function app(options, bootstrapped) {
    window.Galaxy = new GalaxyApp.GalaxyApp(options, bootstrapped);
    Galaxy.debug("login app");
    $(() => {
        Galaxy.page = new Page.View(options);
        var vm = document.createElement("div");
        Galaxy.display(vm);
        var component = Galaxy.params.token ? Password : Login;
        var loginInstance = Vue.extend(component);
        new loginInstance({propsData: options}).$mount(vm);
    });
};
