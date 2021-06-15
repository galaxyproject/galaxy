/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import PageEditor from "./PageEditor";

export const mountPageEditor = (propsData) => {
    const component = Vue.extend(PageEditor);
    return new component({
        propsData: propsData,
        el: "#columns",
    });
};
