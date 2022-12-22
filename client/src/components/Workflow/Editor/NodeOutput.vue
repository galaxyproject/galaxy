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
            <div class="icon prevent-zoom"></div>
        </draggable-wrapper>
    </div>
</template>

<script>
import DraggableWrapper from "./DraggablePan";
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useTerminal } from "./composables/useTerminal";
import { ref, computed, watch, reactive } from "vue";
import { DatatypesMapperModel } from "@/components/Datatypes/model";

export default {
    components: {
        DraggableWrapper,
    },
    props: {
        output: {
            type: Object,
            required: true,
        },
        stepType: {
            type: String,
            required: true,
        },
        stepId: {
            type: Number,
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
        datatypesMapper: {
            type: DatatypesMapperModel,
            required: true,
        },
    },
    setup(props) {
        const el = ref(null);
        const position = useCoordinatePosition(el, props.rootOffset, props.parentOffset, props.stepPosition);
        const extensions = computed(() => {
            const changeDatatype =
                props.postJobActions[`ChangeDatatypeAction${props.output.label}`] ||
                props.postJobActions[`ChangeDatatypeAction${props.output.name}`];
            let extensions =
                changeDatatype?.action_arguments.newtype ||
                props.output.extensions ||
                props.output.type ||
                "unspecified";
            if (!Array.isArray(extensions)) {
                extensions = [extensions];
            }
            return extensions;
        });
        const effectiveOutput = ref({ ...props.output, extensions: extensions.value });
        watch(extensions, () => {
            effectiveOutput.value = { ...props.output, extensions: extensions.value };
        });
        const terminal = useTerminal(ref(props.stepId), effectiveOutput, ref(props.datatypesMapper));
        return { el, position, terminal, extensions };
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
            return `node-${this.stepId}-output-${this.output.name}`;
        },
        label() {
            const activeLabel = this.output.activeLabel || this.output.label || this.output.name;
            return `${activeLabel} (${this.extensions.join(", ")})`;
        },
        activeClass() {
            return this.output.activeOutput && "mark-terminal-active";
        },
        showCallout() {
            return this.stepType == "tool";
        },
        terminalClass() {
            const cls = "terminal output-terminal";
            if (this.isMultiple) {
                return `${cls} multiple`;
            }
            return cls;
        },
    },
    watch: {
        terminalPosition(position) {
            this.$store.commit("workflowState/setOutputTerminalPosition", {
                stepId: this.stepId,
                outputName: this.output.name,
                position,
            });
        },
        dragPosition() {
            if (this.isDragging) {
                const dragConnection = {
                    ...this.dragPosition,
                    terminal: this.terminal,
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
            stepId: this.stepId,
            outputName: this.output.name,
        });
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
