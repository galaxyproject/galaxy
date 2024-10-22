<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt } from "@fortawesome/free-regular-svg-icons";
import { faPalette } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type UseElementBoundingReturn, useFocusWithin } from "@vueuse/core";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { useUid } from "@/composables/utils/uid";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { MarkdownWorkflowComment, WorkflowCommentColor } from "@/stores/workflowEditorCommentStore";

import { darkenedColors } from "./colors";
import { useResizable } from "./useResizable";
import { selectAllText } from "./utilities";

import ColorSelector from "./ColorSelector.vue";
import DraggablePan from "@/components/Workflow/Editor/DraggablePan.vue";

library.add(faTrashAlt, faPalette);

const props = defineProps<{
    comment: MarkdownWorkflowComment;
    rootOffset: UseElementBoundingReturn;
    scale: number;
    readonly?: boolean;
}>();

const emit = defineEmits<{
    (e: "change", data: MarkdownWorkflowComment["data"]): void;
    (e: "resize", size: [number, number]): void;
    (e: "move", position: [number, number]): void;
    (e: "pan-by", position: { x: number; y: number }): void;
    (e: "remove"): void;
    (e: "set-color", color: WorkflowCommentColor): void;
}>();

const resizeContainer = ref<HTMLDivElement>();

useResizable(
    resizeContainer,
    computed(() => props.comment.size),
    ([width, height]) => {
        emit("resize", [width, height]);
    }
);

const textAreaId = useUid("textarea-");

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, increaseHeadingLevelBy: 1 });

const content = computed(() => {
    const renderedMarkdown = renderMarkdown(props.comment.data.text);

    const node = document.createElement("div");
    node.innerHTML = renderedMarkdown;

    // make all rendered text selectable by dragging
    const allChildren = node.querySelectorAll("*");
    Array.from(allChildren).forEach((child) => {
        child.classList.add("prevent-zoom");
    });

    return node.innerHTML;
});

const markdownTextarea = ref<HTMLTextAreaElement>();

function onClick() {
    if (!props.readonly && window.getSelection()?.toString() === "") {
        markdownTextarea.value?.focus();
    }
}

function onMove(position: { x: number; y: number }) {
    emit("move", [position.x, position.y]);
}

function onMouseup() {
    const element = markdownTextarea.value;

    if (element && element.value.trim() === "") {
        element.focus();
    }
}

const showColorSelector = ref(false);
const rootElement = ref<HTMLDivElement>();

const { focused } = useFocusWithin(rootElement);

watch(
    () => focused.value,
    () => {
        if (!focused.value) {
            showColorSelector.value = false;
        }
    }
);

function onSetColor(color: WorkflowCommentColor) {
    emit("set-color", color);
}

function onTextChange() {
    const element = markdownTextarea.value;

    if (element && element.value !== props.comment.data.text) {
        emit("change", { text: element.value });
    }
}

const cssVariables = computed(() => {
    const vars: Record<string, string> = {};

    if (props.comment.color !== "none") {
        vars["--primary-color"] = darkenedColors[props.comment.color];
    }

    return vars;
});

const { commentStore } = useWorkflowStores();

onMounted(() => {
    if (commentStore.isJustCreated(props.comment.id) && markdownTextarea.value) {
        selectAllText(markdownTextarea.value);
    }
});

const position = computed(() => ({ x: props.comment.position[0], y: props.comment.position[1] }));
</script>

<template>
    <div ref="rootElement" class="markdown-workflow-comment">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
        <div
            ref="resizeContainer"
            class="resize-container"
            :class="{
                resizable: !props.readonly,
                'prevent-zoom': !props.readonly,
                'multi-selected': commentStore.getCommentMultiSelected(props.comment.id),
            }"
            :style="cssVariables">
            <DraggablePan
                v-if="!props.readonly"
                :root-offset="reactive(props.rootOffset)"
                :scale="props.scale"
                :position="position"
                :selected="commentStore.getCommentMultiSelected(props.comment.id)"
                class="draggable-pan"
                @mouseup="onMouseup"
                @move="onMove"
                @pan-by="(p) => emit('pan-by', p)" />

            <label :for="textAreaId" class="sr-only">Markdown Input</label>
            <textarea
                :id="textAreaId"
                ref="markdownTextarea"
                class="markdown-textarea prevent-zoom"
                :value="props.comment.data.text"
                @input="onTextChange"></textarea>

            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
            <div class="rendered-markdown" @click="onClick" v-html="content"></div>
        </div>

        <BButtonGroup v-if="!props.readonly" class="style-buttons">
            <BButton
                class="button prevent-zoom"
                variant="outline-primary"
                title="Color"
                :pressed="showColorSelector"
                @click="() => (showColorSelector = !showColorSelector)">
                <FontAwesomeIcon icon="fa-palette" class="prevent-zoom" />
            </BButton>
            <BButton class="button prevent-zoom" variant="dark" title="Delete comment" @click="() => emit('remove')">
                <FontAwesomeIcon icon="far fa-trash-alt" class="prevent-zoom" />
            </BButton>
        </BButtonGroup>

        <ColorSelector
            v-if="showColorSelector"
            class="color-selector"
            :color="props.comment.color"
            @set-color="onSetColor" />
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "buttonGroup.scss";

$gap-x: 0.8rem;
$gap-y: 0.5rem;

$min-width: 1.5em;
$min-height: 1.5em;

.markdown-workflow-comment {
    position: absolute;
    width: 100%;
    height: 100%;

    .resize-container {
        z-index: 50;
    }

    &:focus-within {
        .resize-container {
            resize: both;
        }

        .style-buttons {
            visibility: visible;
        }

        .color-selector {
            visibility: visible;
        }

        .rendered-markdown {
            visibility: hidden;
        }

        .markdown-textarea {
            width: calc(100% - $gap-x - $gap-x);
            height: calc(100% - $gap-y - $gap-y);
        }
    }

    label {
        margin: 0;
        padding: 0;
        height: 100%;
        position: absolute;
        top: 0;
    }

    .markdown-textarea {
        border: none;
        background-color: transparent;
        padding: 0;
        margin: 0;
        resize: none;

        position: absolute;
        top: $gap-y;
        left: $gap-x;

        line-height: 1.2;

        &:focus-visible {
            box-shadow: none;
            border: none;
            outline: none;
        }

        width: 0;
        height: 0;
    }

    .style-buttons {
        visibility: hidden;
        @include button-group-style;
    }
}

.rendered-markdown {
    position: absolute;
    top: $gap-y;
    left: $gap-x;
    overflow-y: auto;
    line-height: 1.2;

    width: calc(100% - $gap-x - $gap-x);
    max-height: calc(100% - $gap-y - $gap-y);

    min-width: $min-width;
    min-height: $min-height;

    &:deep(h2),
    &:deep(h3),
    &:deep(h4),
    &:deep(h5),
    &:deep(h6) {
        margin-bottom: 0.2em;
    }

    &:deep(h2) {
        font-size: $h1-font-size;
    }

    &:deep(h3) {
        font-size: $h2-font-size;
    }

    &:deep(h4) {
        font-size: $h3-font-size;
    }

    &:deep(h5) {
        font-size: $h4-font-size;
    }

    &:deep(h6) {
        font-size: $h5-font-size;
    }

    &:deep(ul),
    &:deep(ol) {
        margin-bottom: 0.5rem;
        padding-left: 1.5rem;
    }

    &:deep(p) {
        margin-bottom: 0.5rem;
    }

    &:deep(blockquote) {
        padding-left: 0.5rem;
        border-left: 2px solid var(--primary-color);
        margin-bottom: 0.5rem;

        p {
            margin-bottom: 0;
        }
    }

    &:deep(a) {
        text-decoration: underline;
    }
}

.resize-container {
    --primary-color: #{$brand-primary};

    color: var(--primary-color);
    background-color: $white;

    .markdown-textarea {
        color: var(--primary-color);
    }

    width: 100%;
    height: 100%;
    min-width: calc($min-width + $gap-x + $gap-x);
    min-height: calc($min-height + $gap-y + $gap-y);
    position: relative;
    overflow: hidden;

    border-radius: 0.25rem;
    border-color: var(--primary-color);
    border-style: solid;
    border-width: 2px;

    .draggable-pan {
        cursor: move;
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
    }

    &.multi-selected {
        box-shadow: 0 0 0 2px $white, 0 0 0 4px lighten($brand-info, 20%);
    }
}

.color-selector {
    visibility: hidden;
    right: 0;
    top: -4.5rem;
}
</style>
