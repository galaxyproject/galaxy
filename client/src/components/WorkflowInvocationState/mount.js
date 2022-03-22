/**
 * Endpoint for mounting workflow invocation state from non-Vue environment.
 */
import $ from "jquery";
import WorkflowInvocationState from "./WorkflowInvocationState.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountWorkflowInvocationState = (propsData = {}) => {
    $(".workflow-invocation-state").each((index, el) => {
        const invocationId = $(el).attr("workflow_invocation_id");
        propsData.invocationId = invocationId;
        mountVueComponent(WorkflowInvocationState)(propsData, el);
    });
};
