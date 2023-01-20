<template>
    <div :class="rowClass">
        <div
            v-if="showCalloutActiveOutput"
            v-b-tooltip
            :class="['callout-terminal', output.name]"
            title="Unchecked outputs will be hidden and are not available as subworkflow outputs."
            @keyup="onToggleActive"
            @click="onToggleActive">
            <i :class="['mark-terminal', activeClass]" />
        </div>
        <div
            v-if="showCalloutVisible"
            v-b-tooltip
            :class="['callout-terminal', output.name]"
            :title="visibleHint"
            @keyup="onToggleVisible"
            @click="onToggleVisible">
            <i :class="['mark-terminal', visibleClass]" />
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
                ref="icon"
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
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

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
            required: true,
        },
        rootOffset: {
            type: Object,
            required: true,
        },
        scroll: {
            type: Object,
            required: true,
        },
        scale: {
            type: Number,
            required: true,
        },
        datatypesMapper: {
            type: DatatypesMapperModel,
            required: true,
        },
    },
    setup(props) {
        const stateStore = useWorkflowStateStore();
        const stepStore = useWorkflowStepStore();
        const el = ref(null);
        const { rootOffset, stepPosition, output, stepId, datatypesMapper } = toRefs(props);
        const position = useCoordinatePosition(el, rootOffset, stepPosition);
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
        const effectiveOutput = ref({ ...output.value, extensions: extensions.value });
        watch(extensions, () => {
            effectiveOutput.value = { ...output.value, extensions: extensions.value };
        });
        const { terminal, isMappedOver: isMultiple } = useTerminal(stepId, effectiveOutput, datatypesMapper);

        const workflowOutput = computed(() =>
            props.workflowOutputs.find((workflowOutput) => workflowOutput.output_name == props.output.name)
        );
        const activeClass = computed(() => workflowOutput.value && "mark-terminal-active");
        const isVisible = computed(() => {
            const isHidden = `HideDatasetAction${props.output.name}` in props.postJobActions;
            return !isHidden;
        });
        const visibleClass = computed(() => (isVisible.value ? "mark-terminal-visible" : "mark-terminal-hidden"));
        const visibleHint = computed(() => {
            if (isVisible.value) {
                return `Output will be visible in history. Click to hide output.`;
            } else {
                return `Output will be hidden in history. Click to make output visible.`;
            }
        });
        const label = computed(() => {
            const activeLabel = workflowOutput.value?.label || props.output.name;
            return `${activeLabel} (${extensions.value.join(", ")})`;
        });
        const rowClass = computed(() => {
            const classes = ["form-row", "dataRow", "output-data-row"];
            if (props.output?.valid === false) {
                classes.push("form-row-error");
            }
            return classes;
        });

        const menu = ref(null);
        const icon = ref(null);
        const showChildComponent = ref(false);

        function closeMenu() {
            showChildComponent.value = false;
        }

        async function toggleChildComponent() {
            showChildComponent.value = !showChildComponent.value;
            if (showChildComponent.value) {
                await nextTick();
                menu.value.$el.focus();
            } else {
                icon.value.focus();
            }
        }

        function onToggleActive() {
            const step = stepStore.getStep(stepId.value);
            if (workflowOutput.value) {
                step.workflow_outputs = step.workflow_outputs.filter(
                    (workflowOutput) => workflowOutput.output_name !== output.value.name
                );
            } else {
                step.workflow_outputs.push({ output_name: output.value.name });
            }
            stepStore.updateStep(step);
        }

        function onToggleVisible() {
            const actionKey = `HideDatasetAction${props.output.name}`;
            const step = stepStore.getStep(stepId.value);
            if (isVisible.value) {
                step.post_job_actions = {
                    ...step.post_job_actions,
                    [actionKey]: {
                        action_type: "HideDatasetAction",
                        output_name: props.output.name,
                        action_arguments: {},
                    },
                };
            } else {
                const { [actionKey]: ignoreUnused, ...newPostJobActions } = step.post_job_actions;
                step.post_job_actions = newPostJobActions;
            }
            stepStore.updateStep(step);
        }

        return {
            el,
            icon,
            position,
            activeClass,
            visibleClass,
            visibleHint,
            rowClass,
            isVisible,
            terminal,
            isMultiple,
            label,
            stateStore,
            menu,
            showChildComponent,
            toggleChildComponent,
            closeMenu,
            effectiveOutput,
            onToggleActive,
            onToggleVisible,
        };
    },
    data() {
        return {
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
            return this.position.left + this.scroll.x.value / this.scale + this.position.width / 2;
        },
        startY() {
            return this.position.top + this.scroll.y.value / this.scale + this.position.height / 2;
        },
        endX() {
            return (this.dragX || this.startX) + this.scroll.x.value / this.scale;
        },
        endY() {
            return (this.dragY || this.startY) + this.scroll.y.value / this.scale;
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
        showCalloutActiveOutput() {
            return this.stepType === "tool" || this.stepType === "subworkflow";
        },
        showCalloutVisible() {
            return this.stepType === "tool";
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
    },
};
</script>
