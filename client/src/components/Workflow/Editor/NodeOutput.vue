<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSquare } from "@fortawesome/free-regular-svg-icons";
import {
    faCheckSquare,
    faChevronCircleRight,
    faEye,
    faEyeSlash,
    faMinus,
    faPlus,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { UseElementBoundingReturn, UseScrollReturn } from "@vueuse/core";
import {
    computed,
    type ComputedRef,
    nextTick,
    onBeforeUnmount,
    type Ref,
    ref,
    toRefs,
    type UnwrapRef,
    watch,
} from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { XYPosition } from "@/stores/workflowEditorStateStore";
import type { OutputTerminalSource, PostJobAction, PostJobActions, Step } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { UpdateStepAction } from "./Actions/stepActions";
import { useRelativePosition } from "./composables/relativePosition";
import { useTerminal } from "./composables/useTerminal";
import { type CollectionTypeDescriptor, NULL_COLLECTION_TYPE_DESCRIPTION } from "./modules/collectionTypeDescription";
import type { OutputTerminals } from "./modules/terminals";

import DraggableWrapper from "./DraggablePan.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import ConnectionMenu from "@/components/Workflow/Editor/ConnectionMenu.vue";

type ElementBounding = UnwrapRef<UseElementBoundingReturn>;

library.add(faSquare, faCheckSquare, faChevronCircleRight, faEye, faEyeSlash, faMinus, faPlus);

const props = defineProps<{
    output: OutputTerminalSource;
    workflowOutputs: NonNullable<Step["workflow_outputs"]>;
    stepType: Step["type"];
    stepId: number;
    postJobActions: PostJobActions;
    stepPosition: Step["position"];
    rootOffset: ElementBounding;
    scroll: UseScrollReturn;
    scale: number;
    datatypesMapper: DatatypesMapperModel;
    parentNode: HTMLElement | null;
    readonly: boolean;
    blank: boolean;
}>();

const emit = defineEmits(["pan-by", "stopDragging", "onDragConnector"]);
const { stateStore, stepStore, undoRedoStore } = useWorkflowStores();
const { rootOffset, output, stepId, datatypesMapper } = toRefs(props);

const terminalComponent: Ref<InstanceType<typeof DraggableWrapper> | null> = ref(null);
const terminalElement = computed(() => (terminalComponent.value?.$el as HTMLElement) ?? null);

const position = useRelativePosition(
    terminalElement,
    computed(() => props.parentNode)
);

const extensions = computed(() => {
    let changeDatatype: PostJobAction | undefined;
    if ("label" in props.output && props.postJobActions[`ChangeDatatypeAction${props.output.label}`]) {
        changeDatatype = props.postJobActions[`ChangeDatatypeAction${props.output.label}`];
    } else {
        changeDatatype = props.postJobActions[`ChangeDatatypeAction${props.output.name}`];
    }
    let extensions =
        changeDatatype?.action_arguments.newtype ||
        ("extensions" in props.output && props.output.extensions) ||
        ("type" in props.output && props.output.type) ||
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

const { terminal, isMappedOver: isMultiple } = useTerminal(stepId, effectiveOutput, datatypesMapper) as {
    terminal: Ref<OutputTerminals>;
    isMappedOver: ComputedRef<boolean>;
};

const workflowOutput = computed(() =>
    props.workflowOutputs.find((workflowOutput) => workflowOutput.output_name == props.output.name)
);

const isVisible = computed(() => {
    const isHidden = `HideDatasetAction${props.output.name}` in props.postJobActions;
    return !isHidden;
});

const visibleHint = computed(() => {
    if (isVisible.value) {
        return `Output will be visible in history. Click to hide output.`;
    } else {
        return `Output will be hidden in history. Click to make output visible.`;
    }
});

const isOutput = computed(() => {
    return Boolean(workflowOutput.value?.label);
});

const label = computed(() => {
    return workflowOutput.value?.label ?? props.output.name;
});

const rowClass = computed(() => {
    const classes = ["form-row", "dataRow", "output-data-row"];
    if ("valid" in props.output && props.output?.valid === false) {
        classes.push("form-row-error");
    }
    return classes;
});

const menu: Ref<InstanceType<typeof ConnectionMenu> | undefined> = ref();
const showChildComponent = ref(false);

function closeMenu() {
    showChildComponent.value = false;
}

async function toggleChildComponent() {
    showChildComponent.value = !showChildComponent.value;
    if (showChildComponent.value) {
        await nextTick();
        if (menu.value?.$el instanceof HTMLElement) {
            menu.value!.$el.focus();
        }
    } else {
        terminalElement.value!.focus();
    }
}

function onToggleActive() {
    if (props.readonly) {
        return;
    }

    const step = stepStore.getStep(stepId.value);
    assertDefined(step);
    let stepWorkflowOutputs = [...(step.workflow_outputs || [])];
    if (workflowOutput.value) {
        stepWorkflowOutputs = stepWorkflowOutputs.filter(
            (workflowOutput) => workflowOutput.output_name !== output.value.name
        );
    } else {
        stepWorkflowOutputs.push({ output_name: output.value.name, label: output.value.name });
    }

    const action = new UpdateStepAction(
        stepStore,
        stateStore,
        step.id,
        { workflow_outputs: step.workflow_outputs },
        { workflow_outputs: stepWorkflowOutputs }
    );
    undoRedoStore.applyAction(action);
}

function onToggleVisible() {
    if (props.readonly) {
        return;
    }

    const actionKey = `HideDatasetAction${props.output.name}`;
    const step = stepStore.getStep(stepId.value);
    assertDefined(step);

    const oldPostJobActions = structuredClone(step.post_job_actions) ?? {};
    let newPostJobActions;

    if (isVisible.value) {
        newPostJobActions = structuredClone(step.post_job_actions) ?? {};
        newPostJobActions[actionKey] = {
            action_type: "HideDatasetAction",
            output_name: props.output.name,
            action_arguments: {},
        };
    } else {
        if (step.post_job_actions) {
            const { [actionKey]: _unused, ...remainingPostJobActions } = step.post_job_actions;
            newPostJobActions = structuredClone(remainingPostJobActions);
        } else {
            newPostJobActions = {};
        }
    }

    const action = new UpdateStepAction(
        stepStore,
        stateStore,
        step.id,
        { post_job_actions: oldPostJobActions },
        { post_job_actions: newPostJobActions }
    );
    undoRedoStore.applyAction(action);
}

function onPanBy(panBy: XYPosition) {
    emit("pan-by", panBy);
}

function onStopDragging() {
    isDragging.value = false;
    dragX.value = 0;
    dragY.value = 0;
    emit("stopDragging");
}

const dragX = ref(0);
const dragY = ref(0);
const isDragging = ref(false);

const startX = computed(
    () => position.value.offsetLeft + (props.stepPosition?.left ?? 0) + (terminalElement.value?.offsetWidth ?? 2) / 2
);
const startY = computed(
    () => position.value.offsetTop + (props.stepPosition?.top ?? 0) + (terminalElement.value?.offsetHeight ?? 2) / 2
);
const endX = computed(() => {
    return (dragX.value || startX.value) + props.scroll.x.value / props.scale;
});
const endY = computed(() => {
    return (dragY.value || startY.value) + props.scroll.y.value / props.scale;
});
const dragPosition = computed(() => {
    return {
        startX: startX.value,
        endX: endX.value,
        startY: startY.value,
        endY: endY.value,
    };
});

watch([dragPosition, isDragging], () => {
    if (isDragging.value) {
        emit("onDragConnector", dragPosition.value, terminal.value);
    }
});

watch(
    [startX, startY],
    ([x, y]) => {
        stateStore.setOutputTerminalPosition(props.stepId, props.output.name, { startX: x, startY: y });
    },
    {
        immediate: true,
    }
);

function onMove(dragPosition: XYPosition) {
    dragX.value = dragPosition.x + terminalElement.value!.clientWidth / 2;
    dragY.value = dragPosition.y + terminalElement.value!.clientHeight / 2;
}

const id = computed(() => `node-${props.stepId}-output-${props.output.name}`);
const showCalloutActiveOutput = computed(() => props.stepType === "tool" || props.stepType === "subworkflow");
const showCalloutVisible = computed(() => props.stepType === "tool");

function collectionTypeToDescription(collectionTypeDescription: CollectionTypeDescriptor) {
    let collectionDescription = collectionTypeDescription.collectionType;
    if (
        collectionTypeDescription &&
        collectionTypeDescription.isCollection &&
        collectionTypeDescription.collectionType
    ) {
        // we'll give a prettier label to the must common nested lists
        switch (collectionTypeDescription.collectionType) {
            case "list:paired": {
                collectionDescription = "list of pairs dataset collection";
                break;
            }
            case "list:list": {
                collectionDescription = "list of lists dataset collection";
                break;
            }
            default: {
                if (collectionTypeDescription.rank > 1) {
                    collectionDescription = `dataset collection with ${collectionTypeDescription.rank} levels of nesting`;
                }
                break;
            }
        }
    }
    return collectionDescription;
}

const outputDetails = computed(() => {
    let collectionType = "collectionType" in terminal.value && terminal.value.collectionType;
    const outputType =
        collectionType && collectionType.isCollection && collectionType.collectionType
            ? `output is ${collectionTypeToDescription(collectionType)}`
            : `output is  ${terminal.value.optional ? "optional " : ""}${terminal.value.type || "dataset"}`;
    if (isMultiple.value) {
        if (!collectionType) {
            collectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        }
        const effectiveOutputType = terminal.value.mapOver.append(collectionType);
        return `${outputType} and mapped-over to produce a ${collectionTypeToDescription(effectiveOutputType)} `;
    }
    return outputType;
});

const isDuplicateLabel = computed(() => {
    const duplicateLabels = stepStore.duplicateLabels;
    return isOutput.value && Boolean(label.value && duplicateLabels.has(label.value));
});

const labelClass = computed(() => {
    if (isDuplicateLabel.value) {
        return "alert-danger";
    }
    return null;
});

const labelToolTipTitle = computed(() => {
    return `Output label '${workflowOutput.value?.label}' is not unique`;
});

onBeforeUnmount(() => {
    stateStore.deleteOutputTerminalPosition(props.stepId, props.output.name);
});

const addTagsAction = computed(() => {
    return props.postJobActions[`TagDatasetAction${props.output.name}`]?.action_arguments?.tags?.split(",") ?? [];
});

const removeTagsAction = computed(() => {
    return props.postJobActions[`RemoveTagDatasetAction${props.output.name}`]?.action_arguments?.tags?.split(",") ?? [];
});
</script>

<template>
    <div class="node-output" :class="rowClass" :data-output-name="output.name">
        <div v-if="!props.blank" class="d-flex flex-column w-100">
            <div class="node-output-buttons">
                <button
                    v-if="showCalloutActiveOutput"
                    v-b-tooltip
                    class="callout-terminal inline-icon-button mark-terminal"
                    :class="{ 'mark-terminal-active': workflowOutput }"
                    title="Checked outputs will become primary workflow outputs and are available as subworkflow outputs."
                    @click="onToggleActive">
                    <FontAwesomeIcon v-if="workflowOutput" fixed-width icon="fa-check-square" />
                    <FontAwesomeIcon v-else fixed-width icon="far fa-square" />
                </button>
                <button
                    v-if="showCalloutVisible"
                    v-b-tooltip
                    class="callout-terminal inline-icon-button mark-terminal"
                    :class="{ 'mark-terminal-visible': isVisible, 'mark-terminal-hidden': !isVisible }"
                    :title="visibleHint"
                    @click="onToggleVisible">
                    <FontAwesomeIcon v-if="isVisible" fixed-width icon="fa-eye" />
                    <FontAwesomeIcon v-else fixed-width icon="fa-eye-slash" />
                </button>
                <span>
                    <span
                        v-b-tooltip
                        :title="labelToolTipTitle"
                        class="d-inline-block rounded"
                        :class="labelClass"
                        :disabled="!isDuplicateLabel">
                        {{ label }}
                    </span>
                    <span> ({{ extensions.join(", ") }}) </span>
                </span>
            </div>

            <div
                v-if="addTagsAction.length > 0"
                v-b-tooltip.left
                class="d-flex align-items-center overflow-x-hidden"
                title="These tags will be added to the output dataset">
                <FontAwesomeIcon icon="fa-plus" class="mr-1" />
                <StatelessTags disabled no-padding :value="addTagsAction" />
            </div>

            <div
                v-if="removeTagsAction.length > 0"
                v-b-tooltip.left
                class="d-flex align-items-center overflow-x-hidden"
                title="These tags will be removed from the output dataset">
                <FontAwesomeIcon icon="fa-minus" class="mr-1" />
                <StatelessTags disabled no-padding :value="removeTagsAction" />
            </div>
        </div>

        <DraggableWrapper
            :id="id"
            ref="terminalComponent"
            v-b-tooltip.hover="!props.blank ? outputDetails : ''"
            class="output-terminal prevent-zoom"
            :class="{ 'mapped-over': isMultiple, 'blank-output': props.blank }"
            :output-name="output.name"
            :root-offset="rootOffset"
            :prevent-default="false"
            :stop-propagation="true"
            :drag-data="{ stepId: stepId, output: effectiveOutput }"
            :draggable="!readonly"
            :disabled="readonly"
            :snappable="false"
            @pan-by="onPanBy"
            @start="isDragging = true"
            @stop="onStopDragging"
            @move="onMove">
            <button
                class="connection-menu-button"
                :aria-label="`Connect output ${output.name} to input. Press space to see a list of available inputs`"
                @click="toggleChildComponent"></button>

            <FontAwesomeIcon class="terminal-icon" icon="fa-chevron-circle-right" />

            <ConnectionMenu
                v-if="showChildComponent"
                ref="menu"
                :terminal="terminal"
                @closeMenu="closeMenu"></ConnectionMenu>
        </DraggableWrapper>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";
@import "nodeTerminalStyle.scss";

.node-output-buttons {
    overflow-wrap: anywhere;
}
.node-output {
    display: flex;
    position: relative;
}

.node-output-buttons {
    display: flex;
    flex-direction: row;
    margin-left: -0.2rem;
}

.output-terminal {
    @include node-terminal-style(right);

    &:not(.blank-output) {
        &:hover {
            color: $brand-success;
        }

        button:focus + .terminal-icon {
            color: $brand-success;
        }
    }
}

.connection-menu-button {
    border: none;
    position: absolute;
    width: 0;
    height: 0;
    padding: 0;
    transition: none;

    &:focus,
    &:focus-visible {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        box-shadow: 0 0 0 0.2rem $brand-primary;
        background-color: $white;
    }
}
</style>
