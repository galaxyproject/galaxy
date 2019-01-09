import $ from "jquery";
import { getAppRoot } from "onload";
import { standardInit, addInitialization } from "onload";
import Page from "layout/page";
import Login from "components/login/Login.vue";
import Password from "components/login/Password.vue";
import Vue from "vue";

export function showOrRedirect(Galaxy, { options }) {
    console.log("showOrRedirect");

    if (!options.show_welcome_with_login) {
        let appRoot = getAppRoot();
        let destination = options.redirect ? options.redirect : appRoot;
        let params = $.param({
            use_panels: "True",
            redirect: encodeURI(destination)
        });
        window.location.href = `${appRoot}user/login?${params}`;
    }
}

export function initLoginView(Galaxy, { options }) {
    console.log("initLoginView");

    /*let pageConfig = Object.assign({}, options, {
        Right: getLoginPage(options)
    });

    Galaxy.page = new Page.View(pageConfig);*/

    Galaxy.page = new Page.View(options);
    var vm = document.createElement("div");
    Galaxy.display(vm);
    var component = Galaxy.params.token || Galaxy.params.expired_user ? Password : Login;
    var loginInstance = Vue.extend(component);
    new loginInstance({propsData: options}).$mount(vm);
}

addInitialization(showOrRedirect, initLoginView);

window.addEventListener("load", () => standardInit("login"));
