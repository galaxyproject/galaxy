<template>
    <raw-connector
        v-if="position"
        :id="connectionId"
        :position="position"
        :output-is-mapped-over="outputIsMappedOver"
        :input-is-mapped-over="inputIsMappedOver"></raw-connector>
</template>

<script lang="ts" setup>
import RawConnector from "@/components/Workflow/Editor/Connector.vue";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import type { Connection } from "@/stores/workflowConnectionStore";
import { computed } from "vue";

const props = defineProps<{
    connection: Connection;
}>();

const stepStore = useWorkflowStepStore();
const outputIsMappedOver = computed(() => stepStore.stepMapOver[props.connection.output.stepId]?.isCollection);
const inputIsMappedOver = computed(() => stepStore.stepMapOver[props.connection.input.stepId]?.isCollection);

const stateStore = useWorkflowStateStore();
const connectionId = computed(() => {
    return `connection-node-${props.connection.input.stepId}-input-${props.connection.input.name}-node-${props.connection.output.stepId}-output-${props.connection.output.name}`;
});
const position = computed(() => {
    const outputPos = stateStore.getOutputTerminalPosition(
        props.connection.output.stepId,
        props.connection.output.name
    );
    const inputPos = stateStore.getInputTerminalPosition(props.connection.input.stepId, props.connection.input.name);
    if (inputPos && outputPos) {
        return { ...inputPos, ...outputPos };
    }
    return null;
});
</script>
