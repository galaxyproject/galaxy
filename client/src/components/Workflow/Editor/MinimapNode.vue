<script lang="ts" setup>
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";
import { computed } from "vue";

const props = defineProps<{
    step: Step;
}>();

const stateStore = useWorkflowStateStore();
const nodePosition = computed(() => stateStore.stepPosition[props.step.id]);

const nodeClass = computed(() => {
    const stateClass = props.step.errors ? "error" : "ok";

    const highlightClass = stateStore.activeNodeId == props.step.id ? "highlight" : "";
    return [stateClass, highlightClass];
});
</script>
<template>
    <rect
        :class="nodeClass"
        :x="step.position.left"
        :y="step.position.top"
        :width="nodePosition.width"
        :height="nodePosition.height" />
</template>
