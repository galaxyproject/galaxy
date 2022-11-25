<template>
    <div class="form-row dataRow input-data-row" @mouseleave="mouseLeave" @mouseover="mouseOver">
        <div :id="id" :input-name="input.name" :class="terminalClass">
            <div ref="el" class="icon" @dragenter="dragOverHandler" @drop="onDrop" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { inject, ref } from "vue";
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
        return { el, position, isDragging, draggingConnection };
    },
    data() {
        return {
            showRemove: false,
            isMultiple: false,
            nodeId: null,
        };
    },
    computed: {
        terminalPosition() {
            return Object.freeze({ endX: this.startX, endY: this.startY });
        },
        startX() {
            return this.position.left + this.position.width / 2;
        },
        startY() {
            return this.position.top + this.position.height / 2;
        },
        id() {
            const node = this.getNode();
            return `node-${node.id}-input-${this.input.name}`;
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
            this.$emit("onDisconnect", this.input.name);
        },
        mouseOver(e) {
            // Need (store?) logic for connections, so we can ask if there are any attached connectors.
            console.log("mouseover");
        },
        mouseLeave() {
            this.showRemove = false;
        },
        onDrop(e) {
            if (this.canAccept) {
                this.$emit("onConnect", {
                    input: { stepId: this.nodeId, name: this.input.name },
                    output: { stepId: this.draggingConnection.id, name: this.draggingConnection.name },
                });
            }
        },
    },
};
</script>
