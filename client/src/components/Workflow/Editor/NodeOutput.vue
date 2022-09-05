<template>
    <div class="form-row dataRow output-data-row">
        <div
            v-if="showCallout"
            v-b-tooltip
            :class="['callout-terminal', output.name]"
            title="Unchecked outputs will be hidden and are not available as subworkflow outputs."
            @click="onToggle">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        {{ label }}
        <draggable-wrapper
            :id="id"
            :class="terminalClass"
            :output-name="output.name"
            :root-offset="rootOffset"
            @pan-by="onPanBy"
            @start="isDragging = true"
            @stopDragging="onStopDragging"
            @move="onMove">
            <div class="icon" ref="terminal"></div>
        </draggable-wrapper>
    </div>
</template>

<script>
import DraggableWrapper from "./Draggable";
import WorkflowConnector from "./Connector";

export default {
    components: {
        DraggableWrapper,
        WorkflowConnector,
    },
    props: {
        output: {
            type: Object,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        postJobActions: {
            type: Object,
            required: true,
        },
        rootOffset: {
            type: Object,
            required: true,
        },
        offsetX: {
            type: Number,
            required: true,
        },
        offsetY: {
            type: Number,
            required: true,
        },
    },
    data() {
        return {
            isMultiple: false,
            isDragging: false,
            initX: 0,
            initY: 0,
            deltaX: 0,
            deltaY: 0,
        };
    },
    mounted() {
        const rect = this.$refs.terminal.getBoundingClientRect();
        this.initX = rect.left + rect.width / 2 - this.rootOffset.left;
        this.initY = rect.top + rect.height / 2 - this.rootOffset.top;
        this.position;
    },
    computed: {
        position() {
            return Object.freeze({ startX: this.startX, startY: this.startY });
        },
        startX() {
            const newX = this.initX + this.offsetX;
            return newX;
        },
        startY() {
            const newY = this.initY + this.offsetY;
            // this.$store.commit("workflowState/setOutputTerminalPosition", this.getNode().id, this.output.name, newY);
            return newY;
        },
        endX() {
            return this.startX + this.deltaX;
        },
        endY() {
            return this.startY + this.deltaY;
        },
        dragPosition() {
            return {
                startX: this.startX,
                endX: this.endX,
                startY: this.startY,
                endY: this.endY,
            };
        },
        id() {
            const node = this.getNode();
            return `node-${node.id}-output-${this.output.name}`;
        },
        label() {
            const activeLabel = this.output.activeLabel || this.output.label || this.output.name;
            return `${activeLabel} (${this.extensions.join(", ")})`;
        },
        activeClass() {
            return this.output.activeOutput && "mark-terminal-active";
        },
        showCallout() {
            const node = this.getNode();
            return node.type == "tool";
        },
        terminalClass() {
            const cls = "terminal output-terminal";
            if (this.isMultiple) {
                return `${cls} multiple`;
            }
            return cls;
        },
        forcedExtension() {
            const changeDatatype =
                this.postJobActions[`ChangeDatatypeAction${this.output.label}`] ||
                this.postJobActions[`ChangeDatatypeAction${this.output.name}`];
            return changeDatatype?.action_arguments.newtype;
        },
        extensions() {
            let extensions = this.forcedExtension || this.output.extensions || this.output.type || "unspecified";
            if (!Array.isArray(extensions)) {
                extensions = [extensions];
            }
            return extensions;
        },
        effectiveOutput() {
            return { ...this.output, extensions: this.extensions };
        },
    },
    watch: {
        position(position) {
            console.log("updating position", position);
            this.$store.commit("workflowState/setOutputTerminalPosition", {
                stepId: this.getNode().id,
                outputName: this.output.name,
                position,
            });
        },
        isDragging() {
            console.log("is dragging ?", this.isDragging);
        },
        dragPosition() {
            console.log("dragPosition", this.endX);
            if (this.isDragging) {
                this.$emit("onDragConnector", this.dragPosition);
            }
        },
        label() {
            // See discussion at: https://github.com/vuejs/vue/issues/8030
            this.$nextTick(() => {
                this.$emit("onChange");
            });
        },
    },
    beforeDestroy() {
        this.$emit("onRemove", this.output);
        // this.terminal.destroy();
    },
    methods: {
        onPanBy(panBy) {
            console.log("panning by", panBy);
            this.$emit("pan-by", panBy);
        },
        onMove(e) {
            console.log("deltax", e.data.deltaX);
            this.deltaX += e.data.deltaX;
            this.deltaY += e.data.deltaY;
        },
        onStopDragging() {
            this.isDragging = false;
            this.deltaX = 0;
            this.deltaY = 0;
            this.$emit("stopDragging");
        },
        inputDragStart(e) {
            console.log("inputDragStart", e);
        },
        inputDragEnter(e) {
            console.log("inputDragEnter", e);
        },
        inputDragLeave(e) {
            console.log("inputDragLeave", e);
        },
        onDrop(e) {
            console.log("onDrop", e);
        },
        onChange() {
            // this.isMultiple = this.terminal.isMappedOver();
            console.log("onChange");
            // this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
