/**
 * Endpoint for mounting workflow invocation state from non-Vue environment.
 */
import $ from "jquery";
import Vue from "vue";
import WorkflowInvocationState from "./WorkflowInvocationState.vue";

export const mountWorkflowInvocationState = (propsData = {}) => {
    $(".workflow-invocation-state").each((index, el) => {
        const invocationId = $(el).attr("workflow_invocation_id");
        const component = Vue.extend(WorkflowInvocationState);
        propsData.invocationId = invocationId;
        return new component({ propsData: propsData }).$mount(el);
    });
};
