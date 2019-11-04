/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import WorkflowEditor from "./WorkflowEditor.vue";

export const mountWorkflowEditor = editorConfig => {
    const propsData = { editorConfig };
    const component = Vue.extend(WorkflowEditor);
    return new component({ propsData: propsData, el: "#center" });
};
