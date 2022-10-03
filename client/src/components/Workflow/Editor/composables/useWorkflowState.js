import store from "store";
import { computed } from "vue";

export function setScale(scale) {
    store.commit("workflowState/setScale", scale);
}

export function useScale() {
    const scale = computed(() => store.getters["workflowState/getScale"]);
    return scale;
}

export function useActiveNodeId() {
    return computed(() => store.getters["workflowState/getActiveNode"]);
}

export function setActiveNodeId(nodeId) {
    store.commit("workflowState/setActiveNode", nodeId);
}
