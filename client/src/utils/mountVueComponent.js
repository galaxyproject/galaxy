// Generic Vue component mount for use in transitional mount functions, Please
// use this instead of your own mount function so that all vue components get
// the same plugins and events.

import BootstrapVue from "bootstrap-vue";
import { createPinia, getActivePinia } from "pinia";
import { createApp, h } from "vue";

import { localizationPlugin, vueRxShortcutPlugin } from "@/components/plugins";

function getOrCreatePinia() {
    // We sometimes use this utility mounting function in a context where there
    // is no existing vue application or pinia store (e.g. individual charts
    // displayed in an iframe).
    // To support both use cases, we will create a new pinia store and attach it
    // to the vue application that is created for the component if missing.
    return getActivePinia() || createPinia();
}

function createConfiguredApp(ComponentDefinition, propsData = {}) {
    const app = createApp({
        render() {
            return h(ComponentDefinition, propsData);
        },
    });
    app.use(getOrCreatePinia());
    app.use(BootstrapVue);
    app.use(localizationPlugin);
    app.use(vueRxShortcutPlugin);
    return app;
}

export function appendVueComponent(ComponentDefinition, options) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const app = createConfiguredApp(ComponentDefinition, options);
    return app.mount(container);
}

export function mountVueComponent(ComponentDefinition) {
    return function (propsData, el) {
        const app = createConfiguredApp(ComponentDefinition, propsData);
        return app.mount(el);
    };
}

export function replaceChildrenWithComponent(el, ComponentDefinition, propsData = {}) {
    const container = document.createElement("div");
    el.replaceChildren(container);
    const mountFn = mountVueComponent(ComponentDefinition);
    return mountFn(propsData, container);
}
