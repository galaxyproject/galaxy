<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, type Ref } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { Connection, OutputTerminal } from "@/stores/workflowConnectionStore";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";

import type { OutputTerminals } from "./modules/terminals";

import SVGConnection from "./SVGConnection.vue";

const props = defineProps<{
    draggingConnection: TerminalPosition | null;
    draggingTerminal: OutputTerminals | null;
    transform: { x: number; y: number; k: number };
    ignoreErrors?: boolean;
}>();

const { connectionStore } = useWorkflowStores();
const { connections } = storeToRefs(connectionStore);

const draggingConnection: Ref<[Connection, TerminalPosition] | null> = computed(() => {
    if (props.draggingConnection && props.draggingTerminal) {
        const connection: Connection = {
            input: {
                connectorType: "input",
                name: "draggingInput",
                stepId: -1,
            },
            output: props.draggingTerminal as unknown as OutputTerminal,
        };

        return [connection, props.draggingConnection];
    } else {
        return null;
    }
});

function key(connection: Connection) {
    return `${connection.input.stepId}-${connection.input.name}-${connection.output.stepId}`;
}

function id(connection: Connection) {
    return `connection-node-${connection.input.stepId}-input-${connection.input.name}-node-${connection.output.stepId}-output-${connection.output.name}`;
}
</script>

<template>
    <div class="workflow-edges">
        <svg class="workflow-edges">
            <SVGConnection
                v-if="draggingConnection"
                :connection="draggingConnection[0]"
                :terminal-position="draggingConnection[1]" />
            <SVGConnection
                v-for="connection in connections"
                :id="id(connection)"
                :key="key(connection)"
                :connection="connection"
                :ignore-errors="props.ignoreErrors" />
        </svg>
    </div>
</template>

<style lang="scss" scoped>
.workflow-edges {
    display: block;
    overflow: visible;
    height: 100%;
    width: 100%;
    left: 0;
    top: 0;
    position: absolute;
    transform-origin: 0 0;
    z-index: 80;
    pointer-events: none;
}
</style>
