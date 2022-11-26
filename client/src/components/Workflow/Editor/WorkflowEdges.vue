<script setup>
import RawConnector from "./Connector";
import TerminalConnector from "./TerminalConnector";
import { computed } from "vue";
import { useConnectionStore } from "stores/workflowConnectionStore";

const props = defineProps({
    steps: {
        type: Object,
        required: true,
    },
    draggingConnection: {
        type: Object,
        default: null,
    },
});

const connectionStore = useConnectionStore();

Object.entries(props.steps).forEach(([stepId, step]) => {
    if (step.input_connections) {
        Object.entries(step?.input_connections).forEach(([input_name, outputArray]) => {
            if (!Array.isArray(outputArray)) {
                outputArray = [outputArray];
            }
            outputArray.forEach((output) => {
                const connection = {
                    id: `${step.id}-${input_name}-${output.id}-${output.output_name}`,
                    input: {
                        stepId: step.id,
                        name: input_name,
                    },
                    output: {
                        stepId: output.id,
                        name: output.output_name,
                    },
                };
                connectionStore.addConnection(connection);
            });
        });
    }
});

const dragStyle = computed(() => {
    // TODO: this isn't quite right, but 6 seems to work, probably because it's the outer strokewidth
    // sync up with Connector.vue ?
    const strokeWidth = 6;
    const dragStyle = {};
    if (props.draggingConnection) {
        dragStyle.left = props.draggingConnection.endX - strokeWidth + "px";
        dragStyle.top = props.draggingConnection.endY - strokeWidth + "px";
    }
    return dragStyle;
});
</script>
<template>
    <div>
        <div v-if="draggingConnection" class="drag-terminal" :style="dragStyle" />
        <svg class="canvas-svg node-area">
            <raw-connector v-if="draggingConnection" :position="draggingConnection"></raw-connector>
            <terminal-connector
                v-for="connection in connectionStore.connections"
                :key="connection.id"
                :connection="connection"></terminal-connector>
        </svg>
    </div>
</template>
