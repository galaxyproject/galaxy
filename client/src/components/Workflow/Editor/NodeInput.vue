<template>
    <div
        class="form-row dataRow input-data-row"
        @mouseleave="leave"
        @mouseenter="enter"
        @focusin="enter"
        @focusout="leave">
        <div
            :id="id"
            :input-name="input.name"
            :class="terminalClass"
            @drop.prevent="onDrop"
            @dragenter.prevent="dragEnter"
            @dragleave.prevent="dragLeave">
            <div :id="iconId" ref="el" v-b-tooltip.manual class="icon" :title="reason" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" @keyup.delete="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { computed } from "@vue/reactivity";
import { inject, ref, toRefs, watchEffect } from "vue";
import { storeToRefs } from "pinia";
import { useTerminal } from "./composables/useTerminal";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";

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
        const { rootOffset, parentOffset, stepPosition, stepId, input, datatypesMapper } = toRefs(props);
        const position = useCoordinatePosition(el, rootOffset, parentOffset, stepPosition);
        const isDragging = inject("isDragging");
        const id = computed(() => `node-${props.stepId}-input-${props.input.name}`);
        const iconId = computed(() => `${id.value}-icon`);
        const connectionStore = useConnectionStore();
        const { terminal, isMappedOver: isMultiple } = useTerminal(stepId, input, datatypesMapper);
        const hasTerminals = ref(false);
        watchEffect(() => {
            hasTerminals.value = connectionStore.getOutputTerminalsForInputTerminal(id.value).length > 0;
        });
        const stateStore = useWorkflowStateStore();
        const { draggingTerminal } = storeToRefs(stateStore);
        return {
            el,
            position,
            isDragging,
            draggingTerminal,
            connectionStore,
            id,
            iconId,
            hasTerminals,
            terminal,
            stateStore,
            isMultiple,
        };
    },
    data() {
        return {
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
            if (this.draggingTerminal) {
                return this.terminal.canAccept(this.draggingTerminal);
            }
            return null;
        },
        reason() {
            const reason = this.canAccept?.reason;
            return reason;
        },
        terminalClass() {
            const classes = ["terminal", "input-terminal", "prevent-zoom"];
            if (this.isDragging) {
                classes.push("input-terminal-active");
                if (this.canAccept?.canAccept) {
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
    },
    watch: {
        terminalPosition(position) {
            this.stateStore.setInputTerminalPosition(this.stepId, this.input.name, position);
        },
    },
    beforeDestroy() {
        this.stateStore.deleteInputTerminalPosition({
            stepId: this.stepId,
            inputName: this.input.name,
        });
    },
    methods: {
        dragEnter(event) {
            if (this.reason) {
                this.$root.$emit("bv::show::tooltip", this.iconId);
            }
            event.preventDefault();
        },
        dragLeave(event) {
            this.$root.$emit("bv::hide::tooltip", this.iconId);
        },
        onChange() {
            this.$emit("onChange");
        },
        onRemove() {
            const connections = this.connectionStore.getConnectionsForTerminal(this.id);
            connections.forEach((connection) => this.terminal.disconnect(connection));
            this.showRemove = false;
        },
        enter() {
            this.showRemove = this.hasTerminals;
        },
        leave() {
            this.showRemove = false;
        },
        onDrop(e) {
            const stepOut = JSON.parse(e.dataTransfer.getData("text/plain"));
            const droppedTerminal = terminalFactory(stepOut.stepId, stepOut.output, this.datatypesMapper);
            this.$root.$emit("bv::hide::tooltip", this.iconId);
            if (this.terminal.canAccept(droppedTerminal).canAccept) {
                this.terminal.connect(droppedTerminal);
            }
        },
    },
};
</script>
