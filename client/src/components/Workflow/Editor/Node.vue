<template>
    <DraggableWrapper
        :id="idString"
        ref="el"
        class="workflow-node card"
        :scale="scale"
        :root-offset="reactive(rootOffset)"
        :position="position"
        :name="name"
        :node-label="title"
        :class="classes"
        :style="style"
        :disabled="readonly"
        :selected="stateStore.getStepMultiSelected(props.id)"
        @move="onMoveTo"
        @pan-by="onPanBy">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
            class="unselectable clearfix card-header py-1 px-2"
            :class="headerClass"
            @pointerdown.exact="onPointerDown"
            @pointerup.exact="onPointerUp"
            @click.shift.capture.prevent.stop="toggleSelected"
            @keyup.enter="makeActive">
            <b-button-group class="float-right">
                <LoadingSpan v-if="isLoading" spinner-only />
                <b-button
                    v-if="!readonly"
                    v-b-tooltip.hover
                    class="node-clone py-0"
                    variant="primary"
                    size="sm"
                    aria-label="clone node"
                    title="Duplicate"
                    @click.prevent.stop="onClone">
                    <i class="fa fa-files-o" />
                </b-button>
                <b-button
                    v-if="!readonly"
                    v-b-tooltip.hover
                    class="node-destroy py-0"
                    variant="primary"
                    size="sm"
                    aria-label="destroy node"
                    title="Remove"
                    @click.prevent.stop="remove">
                    <i class="fa fa-times" />
                </b-button>
                <b-button
                    v-if="isEnabled && !readonly"
                    :id="popoverId"
                    class="node-recommendations py-0"
                    variant="primary"
                    size="sm"
                    aria-label="tool recommendations">
                    <i class="fa fa-arrow-right" />
                </b-button>
                <b-popover
                    v-if="isEnabled && !readonly"
                    :target="popoverId"
                    triggers="hover"
                    placement="bottom"
                    :show.sync="popoverShow">
                    <div>
                        <Recommendations
                            v-if="popoverShow"
                            :step-id="id"
                            :datatypes-mapper="datatypesMapper"
                            @onCreate="onCreate" />
                    </div>
                </b-popover>
            </b-button-group>
            <i :class="iconClass" />
            <span v-if="step.when" v-b-tooltip.hover title="This step is conditionally executed.">
                <FontAwesomeIcon icon="fa-code-branch" />
            </span>
            <span
                v-b-tooltip.hover
                title="Index of the step in the workflow run form. Steps are ordered by distance to the upper-left corner of the window; inputs are listed first."
                >{{ step.id + 1 }}:
            </span>
            <span class="node-title">{{ title }}</span>
            <span class="float-right">
                <FontAwesomeIcon
                    v-if="isInvocation && invocationStep.headerIcon"
                    :icon="invocationStep.headerIcon"
                    :spin="invocationStep.headerIconSpin" />
            </span>
        </div>
        <b-alert
            v-if="!!errors"
            variant="danger"
            show
            class="node-error m-0 rounded-0 rounded-bottom"
            @pointerdown.exact="onPointerDown"
            @pointerup.exact="onPointerUp"
            @click.shift.capture.prevent.stop="toggleSelected">
            {{ errors }}
        </b-alert>
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
            v-else
            class="node-body position-relative card-body p-0 mx-2"
            :class="{ 'cursor-pointer': isInvocation }"
            @pointerdown.exact="onPointerDown"
            @pointerup.exact="onPointerUp"
            @click.shift.capture.prevent.stop="toggleSelected"
            @keyup.enter="makeActive">
            <NodeInput
                v-for="(input, index) in inputs"
                :key="`in-${index}-${input.name}`"
                :class="isInvocation && 'position-absolute'"
                :input="input"
                :blank="isInvocation"
                :step-id="id"
                :datatypes-mapper="datatypesMapper"
                :step-position="step.position ?? { top: 0, left: 0 }"
                :root-offset="rootOffset"
                :scroll="scroll"
                :scale="scale"
                :parent-node="elHtml ?? undefined"
                :readonly="readonly"
                @onChange="onChange" />
            <div v-if="!isInvocation && showRule" class="rule" />
            <NodeInvocationText v-if="isInvocation" :invocation-step="invocationStep" />
            <NodeOutput
                v-for="(output, index) in outputs"
                :key="`out-${index}-${output.name}`"
                :class="isInvocation && 'invocation-node-output'"
                :output="output"
                :workflow-outputs="workflowOutputs"
                :post-job-actions="postJobActions"
                :blank="isInvocation"
                :step-id="id"
                :step-type="step.type"
                :step-position="step.position ?? { top: 0, left: 0 }"
                :root-offset="reactive(rootOffset)"
                :scroll="scroll"
                :scale="scale"
                :datatypes-mapper="datatypesMapper"
                :parent-node="elHtml"
                :readonly="readonly"
                @onDragConnector="onDragConnector"
                @stopDragging="onStopDragging"
                @onChange="onChange" />
        </div>
    </DraggableWrapper>
</template>

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCodeBranch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type UseElementBoundingReturn, type UseScrollReturn, type VueInstance } from "@vueuse/core";
import BootstrapVue from "bootstrap-vue";
import type { PropType, Ref } from "vue";
import Vue, { computed, reactive, ref } from "vue";

import { getGalaxyInstance } from "@/app";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useNodePosition } from "@/components/Workflow/Editor/composables/useNodePosition";
import WorkflowIcons from "@/components/Workflow/icons";
import type { GraphStep } from "@/composables/useInvocationGraph";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { TerminalPosition, XYPosition } from "@/stores/workflowEditorStateStore";
import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";
import type { InputTerminalSource, OutputTerminalSource, Step } from "@/stores/workflowStepStore";
import { composedPartialPath, isClickable } from "@/utils/dom";

import { ToggleStepSelectedAction } from "./Actions/stepActions";
import type { OutputTerminals } from "./modules/terminals";

import LoadingSpan from "@/components/LoadingSpan.vue";
import DraggableWrapper from "@/components/Workflow/Editor/DraggablePan.vue";
import NodeInput from "@/components/Workflow/Editor/NodeInput.vue";
import NodeInvocationText from "@/components/Workflow/Editor/NodeInvocationText.vue";
import NodeOutput from "@/components/Workflow/Editor/NodeOutput.vue";
import Recommendations from "@/components/Workflow/Editor/Recommendations.vue";

Vue.use(BootstrapVue);

library.add(faCodeBranch);

const props = defineProps({
    id: { type: Number, required: true },
    contentId: { type: String as PropType<string | null>, default: null },
    name: { type: String as PropType<string | null>, default: null },
    step: { type: Object as PropType<Step | GraphStep>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    activeNodeId: {
        type: null as unknown as PropType<number | null>,
        required: true,
        validator: (v: any) => typeof v === "number" || v === null,
    },
    rootOffset: { type: Object as PropType<UseElementBoundingReturn>, required: true },
    scroll: { type: Object as PropType<UseScrollReturn>, required: true },
    scale: { type: Number, default: 1 },
    highlight: { type: Boolean, default: false },
    isInvocation: { type: Boolean, default: false },
    readonly: { type: Boolean, default: false },
});

const emit = defineEmits([
    "onRemove",
    "onActivate",
    "onChange",
    "onCreate",
    "onClone",
    "onUpdateStepPosition",
    "pan-by",
    "onDragConnector",
    "stopDragging",
]);

const popoverShow = ref(false);
const popoverId = computed(() => `popover-${props.id}`);
const scrolledTo = ref(false);

function remove() {
    emit("onRemove", props.id);
}

const position = computed(() => ({ x: props.step.position?.left ?? 0, y: props.step.position?.top ?? 0 }));

const el: Ref<VueInstance | null> = ref(null);
const elHtml: Ref<HTMLElement | null> = computed(() => (el.value?.$el as HTMLElement | undefined) ?? null);

const postJobActions = computed(() => props.step.post_job_actions || {});
const workflowOutputs = computed(() => props.step.workflow_outputs || []);
const { connectionStore, stateStore, stepStore, undoRedoStore } = useWorkflowStores();
const isLoading = computed(() => Boolean(stateStore.getStepLoadingState(props.id)?.loading));

useNodePosition(
    elHtml,
    props.id,
    stateStore,
    computed(() => props.scale)
);

const title = computed(() => props.step.label || props.step.name);
const idString = computed(() => `wf-node-step-${props.id}`);
const showRule = computed(() => props.step.inputs?.length > 0 && props.step.outputs?.length > 0);
const iconClass = computed(() => `icon fa fa-fw ${WorkflowIcons[props.step.type]}`);
const isEnabled = getGalaxyInstance().config.enable_tool_recommendations; // getGalaxyInstance is not reactive

const isActive = computed(() => props.id === props.activeNodeId);

const classes = computed(() => {
    return {
        "node-on-scroll-to": scrolledTo.value,
        "node-highlight": props.highlight || isActive.value,
        "is-active": isActive.value,
        "node-multi-selected": stateStore.getStepMultiSelected(props.id),
    };
});

const style = computed(() => {
    return { top: props.step.position!.top + "px", left: props.step.position!.left + "px" };
});

const errors = computed(() => props.step.errors || stateStore.getStepLoadingState(props.id)?.error);

const headerClass = computed(() => {
    return {
        ...invocationStep.value.headerClass,
        "cursor-pointer": props.isInvocation,
        "node-header": !props.isInvocation || invocationStep.value.headerClass === undefined,
        "cursor-move": !props.readonly && !props.isInvocation,
    };
});

const inputs = computed(() => {
    const connections = connectionStore.getConnectionsForStep(props.id);
    const extraStepInputs = stepStore.getStepExtraInputs(props.id);
    const stepInputs = [...extraStepInputs, ...(props.step.inputs || [])];
    const unknownInputs: string[] = [];
    connections.forEach((connection) => {
        if (connection.input.stepId == props.id && !stepInputs.find((input) => input.name === connection.input.name)) {
            unknownInputs.push(connection.input.name);
        }
    });
    const invalidInputNames = [...new Set(unknownInputs)];
    const invalidInputTerminalSource = invalidInputNames.map((name) => {
        const invalidInput: InputTerminalSource = {
            name,
            label: name,
            multiple: false,
            optional: false,
            extensions: [],
            valid: false,
            input_type: "dataset",
        };
        return invalidInput;
    });
    return [...stepInputs, ...invalidInputTerminalSource];
});

const invalidOutputs = computed(() => {
    const connections = connectionStore.getConnectionsForStep(props.id);
    const invalidConnections = connections.filter(
        (connection) =>
            connection.output.stepId == props.id &&
            !props.step.outputs.find((output) => output.name === connection.output.name)
    );
    const invalidOutputNames = [...new Set(invalidConnections.map((connection) => connection.output.name))];
    return invalidOutputNames.map((name) => {
        const invalidOutput: OutputTerminalSource = {
            name,
            optional: false,
            valid: false,
            extensions: [],
        };
        return invalidOutput;
    });
});

const invocationStep = computed(() => props.step as GraphStep);
const outputs = computed(() => {
    return [...props.step.outputs, ...invalidOutputs.value];
});

function onDragConnector(dragPosition: TerminalPosition, terminal: OutputTerminals) {
    emit("onDragConnector", dragPosition, terminal);
}

const mouseMovementThreshold = 9;
const singleClickTimeout = 800;
const doubleClickTimeout = 500;

let mouseDownTime = 0;
let doubleClickTime = 0;

let movementDistance = 0;
let lastPosition: XYPosition | null = null;

const inspectorStore = useWorkflowNodeInspectorStore();

function onPointerDown() {
    mouseDownTime = Date.now();
}

function onPointerUp(e: PointerEvent) {
    const path = composedPartialPath(e);
    const unclickable = path.every((target) => !isClickable(target as Element));

    if (!unclickable) {
        return;
    }

    const mouseUpTime = Date.now();
    const clickTime = mouseUpTime - mouseDownTime;

    if (clickTime <= singleClickTimeout && movementDistance <= mouseMovementThreshold) {
        makeActive();
    }

    const timeBetweenClicks = mouseUpTime - doubleClickTime;

    if (timeBetweenClicks < doubleClickTimeout) {
        inspectorStore.setMaximized(props.step, true);
    }

    doubleClickTime = Date.now();
    lastPosition = null;
    movementDistance = 0;
}

function onMoveTo(position: XYPosition) {
    if (lastPosition) {
        movementDistance += Math.abs(position.x - lastPosition.x);
        movementDistance += Math.abs(position.y - lastPosition.y);
    }

    lastPosition = position;

    emit("onUpdateStepPosition", props.id, {
        top: position.y + props.scroll.y.value / props.scale,
        left: position.x + props.scroll.x.value / props.scale,
    });
}

function onPanBy(panBy: XYPosition) {
    emit("pan-by", panBy);
}

function onStopDragging() {
    emit("stopDragging");
}

function onChange() {
    emit("onChange");
}

function onCreate(contentId: string, name: string) {
    emit("onCreate", contentId, name);
    popoverShow.value = false;
}

function onClone() {
    emit("onClone", props.id);
}

function makeActive() {
    emit("onActivate", props.id);
}

function toggleSelected() {
    undoRedoStore.applyAction(new ToggleStepSelectedAction(stateStore, stepStore, props.id));
}
</script>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-node {
    --dblclick: prevent;

    position: absolute;
    z-index: 100;
    width: $workflow-node-width;
    border: solid $brand-primary 1px;

    $multi-selected: lighten($brand-info, 20%);

    &.node-multi-selected {
        box-shadow: 0 0 0 2px $white, 0 0 0 4px $multi-selected;
    }

    &.node-highlight {
        z-index: 1001;
        border: solid $white 1px;
        box-shadow: 0 0 0 2px $brand-primary;

        &.node-multi-selected {
            box-shadow: 0 0 0 2px $brand-primary, 0 0 0 4px $multi-selected;
        }
    }

    &.node-on-scroll-to {
        z-index: 1001;
        border: solid $white 1px;
        box-shadow: 0 0 0 4px $brand-primary;
        transition: box-shadow 0.5s ease-in-out;
    }

    &.node-active {
        z-index: 1001;
        border: solid $white 1px;
        box-shadow: 0 0 0 3px $brand-primary;

        &.node-multi-selected {
            box-shadow: 0 0 0 3px $brand-primary, 0 0 0 5px $multi-selected;
        }
    }

    .node-header {
        background: $brand-primary;
        color: $white;
        &.cursor-move {
            cursor: move;
        }
    }

    .node-body {
        .invocation-node-output {
            position: absolute;
            right: 0;
            top: 0;
            width: 100%;
            height: 100%;
        }
        .rule {
            height: 0;
            border: none;
            border-bottom: dotted $brand-primary 1px;
            margin: 0 5px;
        }
    }
}
</style>
