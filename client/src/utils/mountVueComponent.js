// Generic Vue component mount for use in transitional
// mount functions

import Vue from "vue";
import store from "../store";
import _l from "utils/localization";

// make localization filter available to all components
Vue.filter("localize", (value) => _l(value));

export const mountVueComponent = (ComponentDefinition) => (propsData, el) => {
    const component = Vue.extend(ComponentDefinition);
    return new component({ store, propsData, el });
};
