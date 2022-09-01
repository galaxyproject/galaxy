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
            @start="isDragging = true"
            @stop="onStopDragging"
            @move="onMove"
            v-on="$listeners">
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
        console.log(rect);
        this.initX = rect.left + rect.width / 2 - this.rootOffset.left;
        this.initY = rect.top + rect.height / 2 - this.rootOffset.top;
    },
    computed: {
        startX() {
            return this.initX + this.offsetX;
        },
        startY() {
            return this.initY + this.offsetY;
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
        isDragging() {
            console.log("is dragging ?", this.isDragging);
        },
        dragPosition() {
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
        onMove(e) {
            this.deltaX += e.data.deltaX;
            this.deltaY += e.data.deltaY;
        },
        onStopDragging() {
            this.isDragging = false;
            this.deltaX = 0;
            this.deltaY = 0;
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
            this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
