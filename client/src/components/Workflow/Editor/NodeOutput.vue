<script setup lang="ts">
import DraggableWrapper from "./DraggablePan.vue";
import { useTerminal } from "./composables/useTerminal";
import { ref, computed, watch, nextTick, toRefs, onBeforeUnmount, type Ref, type UnwrapRef } from "vue";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStateStore, type XYPosition } from "@/stores/workflowEditorStateStore";
import ConnectionMenu from "@/components/Workflow/Editor/ConnectionMenu.vue";
import {
    useWorkflowStepStore,
    type OutputTerminalSource,
    type Step,
    type PostJobActions,
    type PostJobAction,
} from "@/stores/workflowStepStore";
import { assertDefined, ensureDefined } from "@/utils/assertions";
import type { UseElementBoundingReturn, UseScrollReturn } from "@vueuse/core";
import { useRelativePosition } from "./composables/relativePosition";
import { NULL_COLLECTION_TYPE_DESCRIPTION, type CollectionTypeDescriptor } from "./modules/collectionTypeDescription";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import { faPlus, faMinus } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

type ElementBounding = UnwrapRef<UseElementBoundingReturn>;

library.add(faPlus, faMinus);

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
}>();

const emit = defineEmits(["pan-by", "stopDragging", "onDragConnector"]);
const stateStore = useWorkflowStateStore();
const stepStore = useWorkflowStepStore();
const icon: Ref<HTMLElement | null> = ref(null);
const { rootOffset, output, stepId, datatypesMapper } = toRefs(props);

const position = useRelativePosition(
    icon,
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
        icon.value!.focus();
    }
}

function onToggleActive() {
    const step = stepStore.getStep(stepId.value);
    assertDefined(step);
    let stepWorkflowOutputs = [...(step.workflow_outputs || [])];
    if (workflowOutput.value) {
        stepWorkflowOutputs = stepWorkflowOutputs.filter(
            (workflowOutput) => workflowOutput.output_name !== output.value.name
        );
    } else {
        stepWorkflowOutputs.push({ output_name: output.value.name });
    }
    stepStore.updateStep({ ...step, workflow_outputs: stepWorkflowOutputs });
}

function onToggleVisible() {
    const actionKey = `HideDatasetAction${props.output.name}`;
    const step = { ...ensureDefined(stepStore.getStep(stepId.value)) };
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
        if (step.post_job_actions) {
            const { [actionKey]: _unused, ...newPostJobActions } = step.post_job_actions;
            step.post_job_actions = newPostJobActions;
        } else {
            step.post_job_actions = {};
        }
    }
    stepStore.updateStep(step);
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
    () => position.value.offsetLeft + (props.stepPosition?.left ?? 0) + (icon.value?.offsetWidth ?? 2) / 2
);
const startY = computed(
    () => position.value.offsetTop + (props.stepPosition?.top ?? 0) + (icon.value?.offsetHeight ?? 2) / 2
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
    dragX.value = dragPosition.x + icon.value!.clientWidth / 2;
    dragY.value = dragPosition.y + icon.value!.clientHeight / 2;
}

const id = computed(() => `node-${props.stepId}-output-${props.output.name}`);
const showCalloutActiveOutput = computed(() => props.stepType === "tool" || props.stepType === "subworkflow");
const showCalloutVisible = computed(() => props.stepType === "tool");
const terminalClass = computed(() => {
    const cls = "terminal output-terminal";
    if (isMultiple.value) {
        return `${cls} multiple`;
    }
    return cls;
});

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
            : `output is dataset`;
    if (isMultiple.value) {
        if (!collectionType) {
            collectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        }
        const effectiveOutputType = terminal.value.mapOver.append(collectionType);
        return `${outputType} and mapped-over to produce a ${collectionTypeToDescription(effectiveOutputType)} `;
    }
    return outputType;
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
    <div class="d-flex" :class="rowClass" :data-output-name="output.name">
        <div class="d-flex flex-column w-100">
            <div class="d-flex flex-row">
                <div
                    v-if="showCalloutActiveOutput"
                    v-b-tooltip
                    class="callout-terminal"
                    title="Checked outputs will become primary workflow outputs and are available as subworkflow outputs."
                    @keyup="onToggleActive"
                    @click="onToggleActive">
                    <i :class="['mark-terminal', activeClass]" />
                </div>
                <div
                    v-if="showCalloutVisible"
                    v-b-tooltip
                    class="callout-terminal"
                    :title="visibleHint"
                    @keyup="onToggleVisible"
                    @click="onToggleVisible">
                    <i :class="['mark-terminal', visibleClass]" />
                </div>
                {{ label }}
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
                v-b-tooltip.hover="outputDetails"
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
