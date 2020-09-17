/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import InvocationReport from "./InvocationReport";

export const mountInvocationReport = (propsData) => {
    const component = Vue.extend(InvocationReport);
    return new component({
        propsData: propsData,
        el: "#columns",
    });
};
