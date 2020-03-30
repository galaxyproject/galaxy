/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import Index from "./Index";
import Node from "./Node";
import NodeOutput from "./NodeOutput";
import NodeInput from "./NodeInput";

export const mountWorkflowEditor = (propsData) => {
    const component = Vue.extend(Index);
    return new component({
        propsData: propsData,
        el: "#columns",
    });
};

export const mountWorkflowNode = (container, propsData) => {
    const component = Vue.extend(Node);
    return new component({ propsData: propsData, el: container });
};

export const mountWorkflowNodeOutput = (container, propsData) => {
    const component = Vue.extend(NodeOutput);
    return new component({ propsData: propsData, el: container });
};

export const mountWorkflowNodeInput = (container, propsData) => {
    const component = Vue.extend(NodeInput);
    return new component({ propsData: propsData, el: container });
};
