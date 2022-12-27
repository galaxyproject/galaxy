<script setup lang="ts">
import RawConnector from "./Connector.vue";
import TerminalConnector from "./TerminalConnector.vue";
import { computed } from "vue";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { storeToRefs } from "pinia";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import type { OutputTerminal, OutputCollectionTerminal, OutputParameterTerminal } from "./modules/terminals";

interface DraggingConnection extends TerminalPosition {
    terminal: OutputTerminal | OutputCollectionTerminal | OutputParameterTerminal;
}

const props = defineProps<{
    draggingConnection?: DraggingConnection;
}>();

const connectionStore = useConnectionStore();
const { connections } = storeToRefs(connectionStore);

const dragStyle = computed(() => {
    // TODO: this isn't quite right, but 6 seems to work, probably because it's the outer strokewidth
    // sync up with Connector.vue ?
    const strokeWidth = 6;
    const dragStyle: { [index: string]: string } = {};
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
            <raw-connector
                v-if="draggingConnection"
                :position="draggingConnection"
                :input-is-mapped-over="false"
                :output-is-mapped-over="draggingConnection.terminal.mapOver?.isCollection"></raw-connector>
            <terminal-connector
                v-for="connection in connections"
                :key="connection.id"
                :connection="connection"></terminal-connector>
        </svg>
    </div>
</template>
