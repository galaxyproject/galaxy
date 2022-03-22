/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import Index from "./Index";
import store from "store";

export const mountWorkflowEditor = (propsData) => {
    const component = Vue.extend(Index);
    return new component({
        store: store,
        propsData: propsData,
        el: "#columns",
    });
};
