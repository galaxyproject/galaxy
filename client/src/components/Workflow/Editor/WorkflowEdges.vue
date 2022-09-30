<script setup>
import { computed } from "vue";
import RawConnector from "./Connector";
import TerminalConnector from "./TerminalConnector";

const props = defineProps({
    steps: {
        type: Object,
    },
    draggingConnection: {
        type: Object,
        default: null,
    },
});

const connections = computed(() => {
    const connections = [];
    Object.entries(props.steps).forEach(([stepId, step]) => {
        if (step.input_connections) {
            Object.entries(step?.input_connections).forEach(([input_name, outputArray]) => {
                if (!Array.isArray(outputArray)) {
                    outputArray = [outputArray];
                }
                outputArray.forEach((output) => {
                    const connection = {
                        id: `${step.id}-${input_name}-${output.id}-${output.output_name}`,
                        inputStepId: step.id,
                        inputName: input_name,
                        outputStepId: output.id,
                        outputName: output.output_name,
                    };
                    connections.push(connection);
                });
            });
        }
    });
    return connections;
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
                v-for="connection in connections"
                :key="connection.id"
                :connection="connection"></terminal-connector>
        </svg>
    </div>
</template>
