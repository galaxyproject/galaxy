<template>
    <div :class="rowClass" @mouseleave="leave" @mouseenter="enter" @focusin="enter" @focusout="leave">
        <div
            :id="id"
            :input-name="input.name"
            :class="terminalClass"
            @drop.prevent="onDrop"
            @dragenter.prevent="dragEnter"
            @dragleave.prevent="dragLeave">
            <div :id="iconId" ref="el" v-b-tooltip.manual class="icon" :title="reason" />
        </div>
        <div
            v-if="showRemove"
            v-b-tooltip.hover
            :title="reason"
            class="delete-terminal"
            @click="onRemove"
            @keyup.delete="onRemove" />
        {{ label }}
        <span
            v-if="!input.optional && !hasTerminals"
            v-b-tooltip.hover
            class="input-required"
            title="Input is required">
            *
        </span>
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { computed } from "vue";
import { inject, ref, toRefs, watchEffect } from "vue";
import { storeToRefs } from "pinia";
import { useTerminal } from "./composables/useTerminal";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { terminalFactory, ConnectionAcceptable } from "@/components/Workflow/Editor/modules/terminals";

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
            // type UseElementBoundingReturn from "@vueuse/core";
            type: Object,
            required: true,
        },
        scale: {
            type: Number,
            required: true,
        },
        scroll: {
            type: Object,
            required: true,
        },
    },
    setup(props) {
        const el = ref(null);
        const { rootOffset, stepPosition, stepId, input, datatypesMapper } = toRefs(props);
        const position = useCoordinatePosition(el, rootOffset, stepPosition);
        const isDragging = inject("isDragging");
        const id = computed(() => `node-${props.stepId}-input-${props.input.name}`);
        const iconId = computed(() => `${id.value}-icon`);
        const connectionStore = useConnectionStore();
        const { terminal, isMappedOver: isMultiple } = useTerminal(stepId, input, datatypesMapper);
        const hasTerminals = ref(false);
        watchEffect(() => {
            hasTerminals.value = connectionStore.getOutputTerminalsForInputTerminal(id.value).length > 0;
        });

        const rowClass = computed(() => {
            const classes = ["form-row", "dataRow", "input-data-row"];
            if (props.input?.valid === false) {
                classes.push("form-row-error");
            }
            return classes;
        });

        const stateStore = useWorkflowStateStore();
        const { draggingTerminal } = storeToRefs(stateStore);

        const terminalIsHovered = ref(false);
        const connections = computed(() => {
            return connectionStore.getConnectionsForTerminal(id.value);
        });
        const invalidConnectionReasons = computed(() =>
            connections.value
                .map((connection) => connectionStore.invalidConnections[connection.id])
                .filter((reason) => reason)
        );

        const canAccept = computed(() => {
            if (draggingTerminal.value) {
                return terminal.value.canAccept(draggingTerminal.value);
            } else if (invalidConnectionReasons.value.length) {
                return new ConnectionAcceptable(false, invalidConnectionReasons.value[0]);
            }
            return null;
        });

        const showRemove = computed(() => {
            if (invalidConnectionReasons.value.length > 0) {
                return true;
            } else {
                return terminalIsHovered.value && connections.value.length > 0;
            }
        });

        return {
            el,
            position,
            isDragging,
            connectionStore,
            id,
            iconId,
            rowClass,
            canAccept,
            hasTerminals,
            terminal,
            stateStore,
            isMultiple,
            showRemove,
            terminalIsHovered,
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
            return this.position.left + this.scroll.x.value / this.scale + this.position.width / 2;
        },
        startY() {
            return this.position.top + this.scroll.y.value / this.scale + this.position.height / 2;
        },
        label() {
            return this.input.label || this.input.name;
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
            this.terminalIsHovered = false;
        },
        enter() {
            this.terminalIsHovered = true;
        },
        leave() {
            this.terminalIsHovered = false;
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

<style lang="scss" scoped>
@import "theme/blue.scss";
@import "~@fortawesome/fontawesome-free/scss/_variables";

.input-required {
    margin-top: $margin-v * 0.25;
    margin-bottom: $margin-v * 0.25;
    color: $brand-danger;
    font-weight: 300;
    cursor: default;
}
</style>
