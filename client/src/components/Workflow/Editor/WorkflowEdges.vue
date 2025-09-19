<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, type Ref } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { TerminalPosition } from "@/stores/workflowEditorStateStore";
import type { Connection, OutputTerminal } from "@/stores/workflowStoreTypes";

import type { OutputTerminals } from "./modules/terminals";

import SVGConnection from "./SVGConnection.vue";

const props = defineProps<{
    draggingConnection: TerminalPosition | null;
    draggingTerminal: OutputTerminals | null;
    transform: { x: number; y: number; k: number };
    /** Stores the step IDs for steps in the invocation which should have a
     * "breathing" or "flowing" animation applied to their connections.
     */
    stepConnectionClasses?: {
        breathing: number[];
        flowing: number[];
    };
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

/** Checks the connection's input and output step IDs to determine if a "breathing"
 * or "flowing" class should be applied in the `SVGConnection` component.
 */
function getConnectionState(connection: Connection, stateType: "breathing" | "flowing") {
    if (props.stepConnectionClasses) {
        return (
            props.stepConnectionClasses[stateType].includes(connection.output.stepId) ||
            props.stepConnectionClasses[stateType].includes(connection.input.stepId)
        );
    }
    return false;
}
</script>

<template>
    <div class="workflow-edges">
        <svg class="workflow-edges">
            <SVGConnection
                v-if="draggingConnection"
                id="dragging-connection"
                :connection="draggingConnection[0]"
                :terminal-position="draggingConnection[1]" />
            <SVGConnection
                v-for="connection in connections"
                :id="id(connection)"
                :key="key(connection)"
                :connection="connection"
                :flowing="getConnectionState(connection, 'flowing')"
                :breathing="getConnectionState(connection, 'breathing')" />
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
