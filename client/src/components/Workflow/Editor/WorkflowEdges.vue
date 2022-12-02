<script setup>
import RawConnector from "./Connector";
import TerminalConnector from "./TerminalConnector";
import { computed } from "vue";
import { useConnectionStore } from "stores/workflowConnectionStore";
import { storeToRefs } from "pinia";

const props = defineProps({
    draggingConnection: {
        type: Object,
        default: null,
    },
});

const connectionStore = useConnectionStore();
const { connections } = storeToRefs(connectionStore);

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
