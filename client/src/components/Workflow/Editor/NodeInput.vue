<template>
    <div
        class="form-row dataRow input-data-row"
        @mouseleave="leave"
        @mouseenter="enter"
        @focusin="enter"
        @focusout="leave">
        <div :id="id" :input-name="input.name" :class="terminalClass">
            <div ref="el" class="icon" @dragenter="dragOverHandler" @drop="onDrop" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" @keyup.delete="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useConnectionStore } from "stores/workflowConnectionStore";
import { computed } from "@vue/reactivity";
import { inject, ref, watchEffect } from "vue";
import Terminals from "components/Workflow/Editor/modules/terminals";

export default {
    props: {
        input: {
            type: Object,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypesMapper: {
            type: Object,
            required: true,
        },
        stepPosition: {
            type: Object,
            required: true,
        },
        rootOffset: {
            type: Object,
            required: true,
        },
        parentOffset: {
            type: Object,
            required: true,
        },
    },
    setup(props) {
        const el = ref(null);
        const position = useCoordinatePosition(el, props.rootOffset, props.parentOffset, props.stepPosition);
        const isDragging = inject("isDragging");
        const draggingConnection = inject("draggingConnection");
        const id = computed(() => `node-${props.getNode().id}-input-${props.input.name}`);
        const connectionStore = useConnectionStore();
        const connectedTerminals = ref([]);
        watchEffect(() => (connectedTerminals.value = connectionStore.getOutputTerminalsForInputTerminal(id.value)));
        return { el, position, isDragging, draggingConnection, connectionStore, id, connectedTerminals };
    },
    data() {
        return {
            isMultiple: false,
            nodeId: null,
            showRemove: false,
        };
    },
    computed: {
        terminal() {
            return { stepId: this.nodeId, name: this.input.name, connectorType: "input" };
        },
        terminalPosition() {
            return Object.freeze({ endX: this.startX, endY: this.startY });
        },
        startX() {
            return this.position.left + this.position.width / 2;
        },
        startY() {
            return this.position.top + this.position.height / 2;
        },
        label() {
            return this.input.label || this.input.name;
        },
        canAccept() {
            // TODO: put producesAcceptableDatatype ... in datatypesMapper ?
            return Terminals.producesAcceptableDatatype(
                this.datatypesMapper,
                this.input.extensions,
                this.draggingConnection.datatypes
            ).canAccept;
        },
        terminalClass() {
            const classes = ["terminal", "input-terminal", "prevent-zoom"];
            if (this.isDragging) {
                // TODO: check input compatible
                classes.push("input-terminal-active");
                if (this.canAccept) {
                    classes.push("can-accept");
                } else {
                    classes.push("cannot-accept");
                }
            }
            if (this.isMultiple) {
                classes.push("multiple");
            }
            return classes;
        },
        hasTerminals() {
            return this.connectedTerminals.length > 0;
        },
    },
    watch: {
        terminalPosition(position) {
            this.$store.commit("workflowState/setInputTerminalPosition", {
                stepId: this.nodeId,
                inputName: this.input.name,
                position,
            });
        },
    },
    created() {
        this.nodeId = this.getNode().id;
    },
    beforeDestroy() {
        this.$store.commit("workflowState/deleteInputTerminalPosition", {
            stepId: this.nodeId,
            inputName: this.input.name,
        });
    },
    methods: {
        dragOverHandler(event) {
            console.log("dragover input", event);
        },
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onRemove() {
            this.connectionStore.removeConnection(this.terminal);
            this.showRemove = false;
        },
        enter() {
            if (this.hasTerminals) {
                this.showRemove = true;
            } else {
                this.showRemove = false;
            }
        },
        leave() {
            this.showRemove = false;
        },
        onDrop(e) {
            if (this.canAccept) {
                this.$emit("onConnect", {
                    input: this.terminal,
                    output: { stepId: this.draggingConnection.id, name: this.draggingConnection.name },
                });
                this.showRemove = true;
            }
        },
    },
};
</script>
