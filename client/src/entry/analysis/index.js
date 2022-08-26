import { standardInit, addInitialization } from "onload";

import Vue from "vue";
import App from "./App.vue";
import store from "store";
import { getRouter } from "./router";

function buildReactiveMastheadOptions(Galaxy) {
    const props = {
        defaultEnableAdmin: {
            default: Galaxy.user.get("is_admin"),
        },
        defaultEnableInteractiveTools: {
            default: Galaxy.config.interactivetools_enable,
        },
        defaultEnableVisualizations: {
            default: Galaxy.config.visualizations_visible,
        },
    };
    const data = {
        enableAdmin: props.defaultEnableAdmin,
        enableInteractiveTools: props.defaultEnableInteractiveTools,
        enableVisualizations: props.defaultEnableVisualizations,
        activeTab: null,
    };
    const methods = {
        reset() {
            this.enableAdmin = this.defaultEnableAdmin;
            this.enableInteractiveTools = this.defaultEnableInteractiveTools;
            this.enableVisualizations = this.defaultEnableVisualizations;
            this.activeTab = null;
        },
    };
    const vm = new Vue({ props, methods, data });
    return vm;
}

addInitialization((Galaxy) => {
    console.log("App setup");
    const mastheadOptions = buildReactiveMastheadOptions(Galaxy);
    const router = getRouter(Galaxy, mastheadOptions);
    new Vue({
        el: "#app",
        render: (createElement) => createElement(App, { props: { mastheadOptions } }),
        router: router,
        store: store,
    });
    Galaxy.router = router;
});

window.addEventListener("load", () => standardInit("app"));
