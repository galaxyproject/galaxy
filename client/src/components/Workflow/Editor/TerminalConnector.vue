<template>
    <raw-connector
        v-if="position"
        :id="connectionId"
        :position="position"
        :output-is-mapped-over="outputIsMappedOver"
        :input-is-mapped-over="inputIsMappedOver"
        :connection-is-valid="connectionIsValid"
        :nullable="outputIsOptional"></raw-connector>
</template>

<script lang="ts" setup>
import RawConnector from "@/components/Workflow/Editor/Connector.vue";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { useConnectionStore, type Connection } from "@/stores/workflowConnectionStore";
import { computed } from "vue";

const props = defineProps<{
    connection: Connection;
}>();

const stepStore = useWorkflowStepStore();
const connectionStore = useConnectionStore();
const outputIsMappedOver = computed(() => stepStore.stepMapOver[props.connection.output.stepId]?.isCollection);
const inputIsMappedOver = computed(() =>
    Boolean(stepStore.stepInputMapOver[props.connection.input.stepId]?.[props.connection.input.name]?.isCollection)
);
const outputIsOptional = computed(() => {
    return Boolean(
        stepStore.getStep(props.connection.output.stepId)?.when ||
            stepStore
                .getStep(props.connection.output.stepId)
                ?.outputs.find((output) => output.name === props.connection.output.name && output.optional)
    );
});

// move into connection store ?
// move all of terminal logic into connection store ?
const connectionIsValid = computed(() => {
    return !connectionStore.invalidConnections[props.connection.id];
});

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
