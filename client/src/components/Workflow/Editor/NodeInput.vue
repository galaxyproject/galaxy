<template>
    <div class="form-row dataRow input-data-row" @mouseover="mouseOver" @mouseleave="mouseLeave">
        <div :id="id" :input-name="input.name" :class="terminalClass" @drop="onDrop">
            <div ref="el" class="icon" />
        </div>
        <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        {{ label }}
    </div>
</template>

<script>
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { inject, reactive, ref } from "vue";

export default {
    setup(props) {
        const el = ref(null);
        const position = useCoordinatePosition(el, props.rootOffset, props.parentOffset, props.stepPosition);
        const isDragging = inject("isDragging");
        return { el, position, isDragging };
    },
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
    data() {
        return {
            showRemove: false,
            isMultiple: false,
            nodeId: null,
        };
    },
    created() {
        this.nodeId = this.getNode().id;
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
        terminalClass() {
            const classes = ["terminal", "input-terminal"];
            if (this.isDragging) {
                // TODO: check input compatible
                classes.push("input-terminal-active");
                classes.push("can-accept");
            }
            if (this.isMultiple) {
                classes.push("multiple");
            }
            return classes;
        },
    },
    beforeDestroy() {
        this.$emit("onRemove", this.input);
        this.onRemove();
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
    methods: {
        onChange() {
            this.isMultiple = this.terminal.isMappedOver();
            this.$emit("onChange");
        },
        onRemove() {
            this.$emit("onDisconnect", this.input.name);
        },
        mouseOver(e) {},
        mouseLeave() {
            this.showRemove = false;
        },
        onDrop(e) {},
    },
    beforeDestroy() {
        this.$store.commit("workflowState/deleteInputTerminalPosition", {
            stepId: this.nodeId,
            inputName: this.input.name,
        });
    },
};
</script>
