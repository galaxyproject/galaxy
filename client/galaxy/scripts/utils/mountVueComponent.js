// Generic Vue component mount for use in transitional
// mount functions

import Vue from "vue";
import store from "../store"; 

export const mountVueComponent = (ComponentDefinition) => (propsData, el) => {
    // console.log("mount function", propsData);
    let component = Vue.extend(ComponentDefinition);
    return new component({ store, propsData, el });
}
