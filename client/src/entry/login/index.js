import { standardInit, addInitialization } from "onload";
import Page from "layout/page";
import LoginIndex from "components/login/LoginIndex.vue";
import ChangePassword from "components/login/ChangePassword.vue";
import Vue from "vue";

export function initLoginView(Galaxy, { options }) {
    console.log("initLoginView");
    Galaxy.page = new Page.View(options);
    const vm = document.createElement("div");
    Galaxy.display(vm);
    const component = Galaxy.params.token || Galaxy.params.expired_user ? ChangePassword : LoginIndex;
    const loginInstance = Vue.extend(component);
    new loginInstance({
        propsData: {
            show_welcome_with_login: options.show_welcome_with_login,
            welcome_url: options.welcome_url,
            terms_url: options.config.terms_url,
            registration_warning_message: options.config.registration_warning_message,
            mailing_join_addr: options.config.mailing_join_addr,
            server_mail_configured: options.config.server_mail_configured,
        },
    }).$mount(vm);
}

addInitialization(initLoginView);

window.addEventListener("load", () => standardInit("login"));
