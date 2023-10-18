<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt } from "@fortawesome/free-regular-svg-icons";
import { faObjectGroup, faPalette } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type UseElementBoundingReturn, useFocusWithin } from "@vueuse/core";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { sanitize } from "dompurify";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { AxisAlignedBoundingBox, type Rectangle } from "@/components/Workflow/Editor/modules/geometry";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { FrameWorkflowComment, WorkflowComment, WorkflowCommentColour } from "@/stores/workflowEditorCommentStore";
import type { Step } from "@/stores/workflowStepStore";

import { brighterColours, darkenedColours } from "./colours";
import { useResizable } from "./useResizable";
import { selectAllText } from "./utilities";

import ColourSelector from "./ColourSelector.vue";
import DraggablePan from "@/components/Workflow/Editor/DraggablePan.vue";

library.add(faObjectGroup, faTrashAlt, faPalette);

const props = defineProps<{
    comment: FrameWorkflowComment;
    rootOffset: UseElementBoundingReturn;
    scale: number;
    readonly?: boolean;
}>();

const emit = defineEmits<{
    (e: "change", data: FrameWorkflowComment["data"]): void;
    (e: "resize", size: [number, number]): void;
    (e: "move", position: [number, number]): void;
    (e: "pan-by", position: { x: number; y: number }): void;
    (e: "remove"): void;
    (e: "set-colour", colour: WorkflowCommentColour): void;
}>();

const resizeContainer = ref<HTMLDivElement>();

useResizable(
    resizeContainer,
    computed(() => props.comment.size),
    ([width, height]) => {
        emit("resize", [width, height]);
    }
);

function escapeAndSanitize(text: string) {
    return sanitize(text, { ALLOWED_TAGS: [] }).replace(/(?:^(\s|&nbsp;)+)|(?:(\s|&nbsp;)+$)/g, "");
}

const editableElement = ref<HTMLSpanElement>();

function getInnerText() {
    const element = editableElement.value;

    if (element) {
        const value = element.innerHTML ?? "";
        return escapeAndSanitize(value);
    } else {
        return "";
    }
}

function saveText() {
    emit("change", { ...props.comment.data, title: getInnerText() });
}

const showColourSelector = ref(false);
const rootElement = ref<HTMLDivElement>();

const { focused } = useFocusWithin(rootElement);

watch(
    () => focused.value,
    () => {
        if (!focused.value) {
            showColourSelector.value = false;
        }
    }
);

function onClick() {
    editableElement.value?.focus();
}

function onSetColour(colour: WorkflowCommentColour) {
    emit("set-colour", colour);
}

const { stateStore, stepStore, commentStore } = useWorkflowStores();

function getStepsInBounds(bounds: AxisAlignedBoundingBox) {
    const steps: StepWithPosition[] = [];

    Object.values(stepStore.steps).forEach((step) => {
        const rect = stateStore.stepPosition[step.id];

        if (rect && step.position) {
            const stepRect: Rectangle = {
                x: step.position.left,
                y: step.position.top,
                width: rect.width,
                height: rect.height,
            };

            if (bounds.contains(stepRect)) {
                steps.push(step as StepWithPosition);
            }
        }
    });

    return steps;
}

function getCommentsInBounds(bounds: AxisAlignedBoundingBox) {
    const comments: WorkflowComment[] = [];

    commentStore.comments.forEach((comment) => {
        const commentRect: Rectangle = {
            x: comment.position[0],
            y: comment.position[1],
            width: comment.size[0],
            height: comment.size[1],
        };

        if (bounds.contains(commentRect)) {
            comments.push(comment);
        }
    });

    return comments;
}

type StepWithPosition = Step & { position: NonNullable<Step["position"]> };

let stepsInBounds: StepWithPosition[] = [];
let commentsInBounds: WorkflowComment[] = [];
const stepStartOffsets = new Map<number, [number, number]>();
const commentStartOffsets = new Map<number, [number, number]>();

function onDragStart() {
    const aabb = new AxisAlignedBoundingBox();
    aabb.x = props.comment.position[0];
    aabb.y = props.comment.position[1];
    aabb.width = props.comment.size[0];
    aabb.height = props.comment.size[1];

    stepsInBounds = getStepsInBounds(aabb);
    commentsInBounds = getCommentsInBounds(aabb);

    stepsInBounds.forEach((step) => {
        stepStartOffsets.set(step.id, [step.position.left - aabb.x, step.position.top - aabb.y]);
    });

    commentsInBounds.forEach((comment) => {
        commentStartOffsets.set(comment.id, [comment.position[0] - aabb.x, comment.position[1] - aabb.y]);
    });
}

function onDragEnd() {
    saveText();
    stepsInBounds = [];
    commentsInBounds = [];
    stepStartOffsets.clear();
    commentStartOffsets.clear();
}

function onMove(position: { x: number; y: number }) {
    stepsInBounds.forEach((step) => {
        const stepPosition = { left: 0, top: 0 };
        const offset = stepStartOffsets.get(step.id) ?? [0, 0];
        stepPosition.left = position.x + offset[0];
        stepPosition.top = position.y + offset[1];
        stepStore.updateStep({ ...step, position: stepPosition });
    });

    commentsInBounds.forEach((comment) => {
        const offset = commentStartOffsets.get(comment.id) ?? [0, 0];
        const commentPosition = [position.x + offset[0], position.y + offset[1]] as [number, number];
        commentStore.changePosition(comment.id, commentPosition);
    });

    emit("move", [position.x, position.y]);
}

function onDoubleClick() {
    if (editableElement.value) {
        selectAllText(editableElement.value);
    }
}

const cssVariables = computed(() => {
    const vars: Record<string, string> = {};

    if (props.comment.colour !== "none") {
        vars["--primary-colour"] = darkenedColours[props.comment.colour];
        vars["--secondary-colour"] = brighterColours[props.comment.colour];
    }

    return vars;
});

onMounted(() => {
    if (commentStore.isJustCreated(props.comment.id) && editableElement.value) {
        selectAllText(editableElement.value);
    }
});
</script>

<template>
    <div ref="rootElement" class="frame-workflow-comment">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
        <div
            ref="resizeContainer"
            class="resize-container"
            :class="{ resizable: !props.readonly, 'prevent-zoom': !props.readonly }"
            :style="cssVariables"
            @click="onClick">
            <DraggablePan
                v-if="!props.readonly"
                :root-offset="reactive(props.rootOffset)"
                :scale="props.scale"
                class="draggable-pan"
                @move="onMove"
                @mouseup="onDragEnd"
                @start="onDragStart"
                @pan-by="(p) => emit('pan-by', p)" />

            <div class="frame-comment-header">
                <FontAwesomeIcon icon="fas fa-object-group" />
                <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
                <span
                    ref="editableElement"
                    :contenteditable="!props.readonly"
                    class="prevent-zoom"
                    spellcheck="false"
                    @blur="saveText"
                    @keydown.enter.prevent="saveText"
                    @dblclick.prevent="onDoubleClick"
                    @mouseup.stop
                    v-html="escapeAndSanitize(props.comment.data.title)" />
            </div>
        </div>

        <BButtonGroup v-if="!props.readonly" class="style-buttons">
            <BButton
                class="button prevent-zoom"
                variant="outline-primary"
                title="Colour"
                :pressed="showColourSelector"
                @click="() => (showColourSelector = !showColourSelector)">
                <FontAwesomeIcon icon="fa-palette" class="prevent-zoom" />
            </BButton>
            <BButton class="button prevent-zoom" variant="dark" title="Delete comment" @click="() => emit('remove')">
                <FontAwesomeIcon icon="far fa-trash-alt" class="prevent-zoom" />
            </BButton>
        </BButtonGroup>

        <ColourSelector
            v-if="showColourSelector"
            class="colour-selector"
            :colour="props.comment.colour"
            @set-colour="onSetColour" />
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "buttonGroup.scss";

.frame-workflow-comment {
    width: 100%;
    height: 100%;

    .resize-container {
        z-index: 0;
    }

    &:focus-within {
        .resize-container {
            resize: both;
        }

        .colour-selector {
            visibility: visible;
        }

        .style-buttons {
            visibility: visible;
        }
    }

    .style-buttons {
        visibility: hidden;
        @include button-group-style;
    }
}

.resize-container {
    --primary-colour: #{$brand-primary};
    --secondary-colour: #{$white};

    color: var(--primary-colour);
    width: 100%;
    height: 100%;
    min-height: 100px;
    min-width: 100px;
    position: relative;
    overflow: hidden;

    border-radius: 0.25rem;
    border-color: var(--primary-colour);
    border-style: solid;
    border-width: 2px;

    .frame-comment-header {
        background-color: var(--primary-colour);
        color: $white;
        font-size: 1rem;
        padding: 0.1rem 0.5rem;
        position: relative;
        pointer-events: none;

        span {
            position: relative;
            pointer-events: all;
        }

        span:focus,
        span:focus-visible {
            border: none;
            outline: none;
            box-shadow: none;
        }
    }

    .draggable-pan {
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        cursor: move;
    }

    // coloring the "background" via ::after avoids zooming artifacts on the header
    display: flex;
    flex-direction: column;
    background-color: var(--primary-colour);

    &::after {
        content: "";
        display: block;
        background-color: var(--secondary-colour);
        flex: 1;
        position: relative;
    }
}

.colour-selector {
    visibility: hidden;
    right: 0;
    top: -4.5rem;
}
</style>
