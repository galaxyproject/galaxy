// Generic Vue component mount for use in transitional mount functions, Please
// use this instead of your own mount function so that all vue components get
// the same plugins and events.

import BootstrapVue from "bootstrap-vue";
import { createPinia, getActivePinia } from "pinia";
import { createApp, h } from "vue";

import { localizationPlugin } from "@/components/plugins";
import { vGTooltip } from "@/directives/vGTooltip";
import { vNoSanitizeHtml } from "@/directives/vNoSanitizeHtml";
import { vSanitizeHtml } from "@/directives/vSanitizeHtml";

function getOrCreatePinia() {
    // We sometimes use this utility mounting function in a context where there
    // is no existing vue application or pinia store (e.g. individual charts
    // displayed in an iframe).
    // To support both use cases, we will create a new pinia store and attach it
    // to the vue application that is created for the component if missing.
    return getActivePinia() || createPinia();
}

// Plugins every Galaxy app needs, shared by the main analysis app and the
// transitional apps mounted below.
export function installAppPlugins(app) {
    app.use(BootstrapVue);
    app.use(localizationPlugin);
    app.directive("g-tooltip", vGTooltip);
    // Renders markup through DOMPurify; the replacement for raw v-html
    app.directive("sanitize-html", vSanitizeHtml);
    // Unsanitized markup from the server or shipped code; each use documents why
    app.directive("no-sanitize-html", vNoSanitizeHtml);
}

function createConfiguredApp(ComponentDefinition, propsData = {}) {
    const app = createApp({
        render() {
            return h(ComponentDefinition, propsData);
        },
    });
    app.use(getOrCreatePinia());
    installAppPlugins(app);
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
