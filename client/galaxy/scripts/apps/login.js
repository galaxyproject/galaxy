import jQuery from "jquery";
var $ = jQuery;
import GalaxyApp from "galaxy";
import Page from "layout/page";
import Login from "components/Login.vue";
import Vue from "vue";

window.app = function app(options, bootstrapped) {
    window.Galaxy = new GalaxyApp.GalaxyApp(options, bootstrapped);
    Galaxy.debug("login app");
    $(() => {
        Galaxy.page = new Page.View(
            _.extend(options, {
                Right: Vue.extend(Login)
            })
        );
    });
};
