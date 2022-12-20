<template>
    <div
        class="form-row dataRow input-data-row"
        @mouseleave="leave"
        @mouseenter="enter"
        @focusin="enter"
        @focusout="leave">
        <div :id="id" :input-name="input.name" :class="terminalClass">
            <div
                :id="iconId"
                ref="el"
                class="icon"
                @dragenter="dragEnter"
                @dragleave="dragLeave"
                @drop="onDrop"
                v-b-tooltip.manual
                :title="reason" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" @keyup.delete="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { computed } from "@vue/reactivity";
import { inject, ref, watchEffect } from "vue";
import { useTerminal } from "./composables/useTerminal";
import { DatatypesMapperModel } from "@/components/Datatypes/model";

export default {
    props: {
        input: {
            type: Object,
            required: true,
        },
        stepId: {
            type: Number,
            required: true,
        },
        datatypesMapper: {
            type: DatatypesMapperModel,
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
        const id = computed(() => `node-${props.stepId}-input-${props.input.name}`);
        const iconId = computed(() => `${id.value}-icon`);
        const connectionStore = useConnectionStore();
        const connectedTerminals = ref([]);
        watchEffect(() => (connectedTerminals.value = connectionStore.getOutputTerminalsForInputTerminal(id.value)));
        const terminal = useTerminal(ref(props.stepId), ref(props.input), ref(props.datatypesMapper));
        return {
            el,
            position,
            isDragging,
            draggingConnection,
            connectionStore,
            id,
            iconId,
            connectedTerminals,
            terminal,
        };
    },
    data() {
        return {
            isMultiple: false,
            showRemove: false,
        };
    },
    computed: {
        terminalArgs() {
            return { stepId: this.stepId, name: this.input.name, connectorType: "input" };
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
            return this.draggingConnection && this.terminal.canAccept(this.draggingConnection.terminal);
        },
        reason() {
            const reason = this.canAccept?.reason;
            return reason;
        },
        terminalClass() {
            const classes = ["terminal", "input-terminal", "prevent-zoom"];
            if (this.isDragging) {
                classes.push("input-terminal-active");
                if (this.canAccept.canAccept) {
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
                stepId: this.stepId,
                inputName: this.input.name,
                position,
            });
        },
    },
    beforeDestroy() {
        this.$store.commit("workflowState/deleteInputTerminalPosition", {
            stepId: this.stepId,
            inputName: this.input.name,
        });
    },
    methods: {
        dragEnter(event) {
            if (this.reason) {
                this.$root.$emit("bv::show::tooltip", this.iconId);
            }
            console.log("dragover input", event);
        },
        dragLeave(event) {
            this.$root.$emit("bv::hide::tooltip", this.iconId);
        },
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onRemove() {
            const connections = this.connectionStore.getConnectionsForTerminal(this.id);
            connections.forEach((connection) => this.terminal.disconnect(connection));
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
            if (this.canAccept.canAccept) {
                this.terminal.connect(this.draggingConnection.terminal);
                this.showRemove = true;
                this.$root.$emit("bv::hide::tooltip", this.iconId);
            }
        },
    },
};
</script>
