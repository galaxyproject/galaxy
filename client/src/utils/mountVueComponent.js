// Generic Vue component mount for use in transitional mount functions, Please
// use this instead of your own mount function so that all vue components get
// the same plugins and events.

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import store from "../store";

import {
    // legacyNavigationPlugin,
    eventHubPlugin,
    localizationPlugin,
    vueRxShortcutPlugin,
} from "components/plugins";

// Bootstrap components
Vue.use(BootstrapVue);

// Install horrible plugin for navigation with backbone client
// Vue.use(legacyNavigationPlugin);

// Add a global event bus. We could just use root but I don't think that will
// work right when we have more than one root, which we often will until the
// application has been completely converted to Vue.
Vue.use(eventHubPlugin);

// localization filters and directives
Vue.use(localizationPlugin);

// rxjs utilities
Vue.use(vueRxShortcutPlugin);

export const mountVueComponent = (ComponentDefinition) => {
    const component = Vue.extend(ComponentDefinition);
    return (propsData, el) => new component({ store, propsData, el });
};
