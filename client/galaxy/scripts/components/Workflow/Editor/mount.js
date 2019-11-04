/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import WorkflowEditor from "./WorkflowEditor.vue";

export const mountWorkflowEditor = (el, name) => {
    const propsData = { name };
    const component = Vue.extend(WorkflowEditor);
    return new component({ propsData: propsData }).$mount(el);
};
