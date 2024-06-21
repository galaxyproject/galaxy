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
    // To support both use cases, we will create a new pinia store and attach it to the
    // vue application that is created for the component.
    let pinia = getActivePinia();
    if (!pinia) {
        pinia = createPinia();
    }
    return pinia;
}

export const mountVueComponent = (ComponentDefinition) => {
    const component = Vue.extend(ComponentDefinition);
    return (propsData, el) => new component({ propsData, el, pinia: getOrCreatePinia() });
};

export const replaceChildrenWithComponent = (el, ComponentDefinition, propsData = {}) => {
    const container = document.createElement("div");
    el.replaceChildren(container);
    const component = Vue.extend(ComponentDefinition);
    const mountFn = (propsData, el) => new component({ propsData, el, pinia: getOrCreatePinia() });
    return mountFn(propsData, container);
};
