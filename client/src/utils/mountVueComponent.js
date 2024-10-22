// Generic Vue component mount for use in transitional mount functions, Please
// use this instead of your own mount function so that all vue components get
// the same plugins and events.

import BootstrapVue from "bootstrap-vue";
import { iconPlugin, localizationPlugin, vueRxShortcutPlugin } from "components/plugins";
import { createPinia, getActivePinia, PiniaVuePlugin } from "pinia";
import Vue from "vue";

// Load Pinia
Vue.use(PiniaVuePlugin);

// Bootstrap components
Vue.use(BootstrapVue);

// localization filters and directives
Vue.use(localizationPlugin);

// rxjs utilities
Vue.use(vueRxShortcutPlugin);

// font-awesome svg icon registration/loading
Vue.use(iconPlugin);

function getOrCreatePinia() {
    // We sometimes use this utility mounting function in a context where there
    // is no existing vue application or pinia store (e.g. individual charts
    // displayed in an iframe).
    // To support both use cases, we will create a new pinia store and attach it
    // to the vue application that is created for the component if missing.
    return getActivePinia() || createPinia();
}

export function mountVueComponent(ComponentDefinition) {
    const component = Vue.extend(ComponentDefinition);
    return function (propsData, el) {
        return new component({ propsData, el, pinia: getOrCreatePinia() });
    };
}

export function replaceChildrenWithComponent(el, ComponentDefinition, propsData = {}) {
    const container = document.createElement("div");
    el.replaceChildren(container);
    const mountFn = mountVueComponent(ComponentDefinition);
    return mountFn(propsData, container);
}
