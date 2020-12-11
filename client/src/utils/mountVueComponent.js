// Generic Vue component mount for use in transitional
// mount functions, Please use this instead of your own mount
// function so that all vue components get the same plugins
// and events.

import Vue from "vue";
import VueRx from "vue-rx";
import BootstrapVue from "bootstrap-vue";
import store from "../store";
import _l from "utils/localization";
import { legacyNavigationPlugin, eventHubPlugin } from "components/plugins";

// Bootstrap components
Vue.use(BootstrapVue);

// adds subscriptions to components
Vue.use(VueRx);

// make localization filter available to all components
Vue.filter("localize", (value) => _l(value));
Vue.filter("l", (value) => _l(value));

// can also localize a block of text
const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;
Vue.directive("localize", {
    bind(el, binding, vnode) {
        el.childNodes.forEach((node) => {
            const oneline = node.textContent.replace(newlineMatch, " ");
            const singleSpaces = oneline.replace(doublespaces, " ");
            node.textContent = _l(singleSpaces);
        });
    },
});

// Install horrible plugin for navigation with backbone client
Vue.use(legacyNavigationPlugin);

// Add a global event bus. We could just use root but I don't think that will
// work right when we have more than one root, which we often will until the application
// has been completely converted to Vue.
Vue.use(eventHubPlugin);

export const mountVueComponent = (ComponentDefinition) => (propsData, el) => {
    const component = Vue.extend(ComponentDefinition);
    return new component({ store, propsData, el });
};
