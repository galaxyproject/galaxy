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
            ref="el"
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
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { reactive, ref } from "vue";

export default {
    setup(props) {
        const el = ref(null);
        const position = useCoordinatePosition(el, props.rootOffset, props.parentOffset, props.stepPosition);
        return { el, position };
    },
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
        postJobActions: {
            type: Object,
            required: true,
        },
        stepPosition: {
            type: Object,
        },
        rootOffset: {
            type: Object,
            required: true,
        },
        parentOffset: {
            type: Object,
            default: {},
        },
    },
    data() {
        return {
            isMultiple: false,
            isDragging: false,
            deltaX: 0,
            deltaY: 0,
        };
    },
    computed: {
        terminalPosition() {
            return Object.freeze({ startX: this.startX, startY: this.startY });
        },
        initX() {
            return this.position.left + this.position.width / 2;
        },
        initY() {
            return this.position.top + this.position.height / 2;
        },
        startX() {
            return this.initX;
        },
        startY() {
            return this.initY;
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
        terminalPosition(position) {
            this.$store.commit("workflowState/setOutputTerminalPosition", {
                stepId: this.getNode().id,
                outputName: this.output.name,
                position,
            });
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
        this.$store.commit("workflowState/deleteOutputTerminalPosition", {
            stepId: this.getNode().id,
            outputName: this.output.name,
        });
        this.$emit("onRemove", this.output);
    },
    methods: {
        onPanBy(panBy) {
            this.$emit("pan-by", panBy);
        },
        onMove(e) {
            this.deltaX += e.data.deltaX;
            this.deltaY += e.data.deltaY;
        },
        onStopDragging() {
            this.isDragging = false;
            this.deltaX = 0;
            this.deltaY = 0;
            this.$emit("stopDragging");
        },
        inputDragStart(e) {},
        inputDragEnter(e) {},
        inputDragLeave(e) {},
        onDrop(e) {},
        onChange() {
            // this.isMultiple = this.terminal.isMappedOver();
            // this.$emit("onChange");
        },
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
