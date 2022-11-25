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
            ref="el"
            :class="terminalClass"
            :output-name="output.name"
            :root-offset="rootOffset"
            :prevent-default="false"
            :stop-propagation="true"
            draggable="true"
            @dragstart="dragStart"
            @pan-by="onPanBy"
            @start="isDragging = true"
            @stop="onStopDragging"
            @move="onMove">
            <div ref="terminal" class="icon prevent-zoom"></div>
        </draggable-wrapper>
    </div>
</template>

<script>
import DraggableWrapper from "./DraggablePan";
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { ref } from "vue";

export default {
    components: {
        DraggableWrapper,
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
        },
    },
    setup(props) {
        const el = ref(null);
        const position = useCoordinatePosition(el, props.rootOffset, props.parentOffset, props.stepPosition);
        return { el, position };
    },
    data() {
        return {
            isMultiple: false,
            isDragging: false,
            dragX: 0,
            dragY: 0,
        };
    },
    computed: {
        terminalPosition() {
            return Object.freeze({ startX: this.startX, startY: this.startY });
        },
        startX() {
            return this.position.left + this.position.width / 2;
        },
        startY() {
            return this.position.top + this.position.height / 2;
        },
        endX() {
            return this.dragX || this.startX;
        },
        endY() {
            return this.dragY || this.startY;
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
                const dragConnection = {
                    ...this.dragPosition,
                    datatypes: this.extensions,
                    id: this.getNode().id,
                    name: this.output.name,
                };
                this.$emit("onDragConnector", dragConnection);
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
        debugHandler(event) {
            console.log("debug", event);
        },
        onPanBy(panBy) {
            this.$emit("pan-by", panBy);
        },
        onMove(position, event) {
            this.dragX = position.x + this.position.width / 2;
            this.dragY = position.y + this.position.height / 2;
        },
        onStopDragging(e) {
            this.isDragging = false;
            this.dragX = 0;
            this.dragY = 0;
            this.$emit("stopDragging");
        },
        dragStart(e) {
            console.log("dragStart", e);
        },
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
