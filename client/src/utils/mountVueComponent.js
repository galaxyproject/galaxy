// Generic Vue component mount for use in transitional mount functions, Please
// use this instead of your own mount function so that all vue components get
// the same plugins and events.

import Vue from "vue";
import Vuex from "vuex";
import frag from "vue-frag";
import BootstrapVue from "bootstrap-vue";
import store from "../store";
import { eventHubPlugin, localizationPlugin, vueRxShortcutPlugin } from "components/plugins";

Vue.use(Vuex);

// Bootstrap components
Vue.use(BootstrapVue);

// Add a global event bus. We could just use root but I don't think that will
// work right when we have more than one root, which we often will until the
// application has been completely converted to Vue.
Vue.use(eventHubPlugin);

// localization filters and directives
Vue.use(localizationPlugin);

// rxjs utilities
Vue.use(vueRxShortcutPlugin);

// fragment unwrapper, gets around multi-root limitation which causes us to
// render extraneous nested elements, often breaking things like standard HTML tables
Vue.directive("frag", frag);

export const mountVueComponent = (ComponentDefinition) => {
    const component = Vue.extend(ComponentDefinition);
    return (propsData, el) => new component({ store, propsData, el });
};
