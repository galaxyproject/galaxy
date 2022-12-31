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
            :drag-data="{ stepId: stepId, output: effectiveOutput }"
            draggable="true"
            @pan-by="onPanBy"
            @start="isDragging = true"
            @stop="onStopDragging"
            @move="onMove">
            <div
                class="icon prevent-zoom"
                tabindex="0"
                :aria-label="`Connect output ${output.name} to input. Press space to see a list of available inputs`"
                @keyup.space="toggleChildComponent"
                @keyup.enter="toggleChildComponent"
                @keyup.esc="toggleChildComponent">
                <connection-menu
                    v-if="showChildComponent"
                    ref="menu"
                    :terminal="terminal"
                    @closeMenu="closeMenu"></connection-menu>
            </div>
        </draggable-wrapper>
    </div>
</template>

<script>
import DraggableWrapper from "./DraggablePan";
import { useCoordinatePosition } from "./composables/useCoordinatePosition";
import { useTerminal } from "./composables/useTerminal";
import { ref, computed, watch, nextTick, toRefs } from "vue";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import ConnectionMenu from "@/components/Workflow/Editor/ConnectionMenu";

export default {
    components: {
        ConnectionMenu,
        DraggableWrapper,
    },
    props: {
        output: {
            type: Object,
            required: true,
        },
        workflowOutputs: {
            type: Array,
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
        const { rootOffset, parentOffset, stepPosition } = toRefs(props);
        const position = useCoordinatePosition(el, rootOffset, parentOffset, stepPosition);
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

        function closeMenu() {
            showChildComponent.value = false;
        }

        const label = computed(() => {
            const workflowOutput = props.workflowOutputs.find(
                (workflowOutput) => workflowOutput.output_name == props.output.name
            );
            const activeLabel = workflowOutput?.label || props.output.name;
            return `${activeLabel} (${extensions.value.join(", ")})`;
        });

        const menu = ref(null);
        const showChildComponent = ref(false);
        async function toggleChildComponent() {
            showChildComponent.value = !showChildComponent.value;
            if (showChildComponent.value) {
                await nextTick();
                menu.value.$el.focus();
            }
        }

        const stateStore = useWorkflowStateStore();
        return {
            el,
            position,
            terminal,
            label,
            stateStore,
            menu,
            showChildComponent,
            toggleChildComponent,
            closeMenu,
            effectiveOutput,
        };
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
            this.stateStore.setOutputTerminalPosition(this.stepId, this.output.name, position);
        },
        dragPosition() {
            if (this.isDragging) {
                this.$emit("onDragConnector", this.dragPosition, this.terminal);
            }
        },
    },
    beforeDestroy() {
        this.stateStore.deleteOutputTerminalPosition({
            stepId: this.stepId,
            outputName: this.output.name,
        });
    },
    methods: {
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
        onToggle() {
            this.$emit("onToggle", this.output.name);
        },
    },
};
</script>
