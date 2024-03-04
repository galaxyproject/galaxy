<script setup lang="ts">
import { type UseElementBoundingReturn } from "@vueuse/core";
import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment, WorkflowCommentColor } from "@/stores/workflowEditorCommentStore";

import {
    ChangeColorAction,
    DeleteCommentAction,
    LazyChangeDataAction,
    LazyChangePositionAction,
    LazyChangeSizeAction,
} from "../Actions/commentActions";
import { useMultiSelect } from "../composables/multiSelect";

import FrameComment from "./FrameComment.vue";
import FreehandComment from "./FreehandComment.vue";
import MarkdownComment from "./MarkdownComment.vue";
import TextComment from "./TextComment.vue";

const props = defineProps<{
    comment: WorkflowComment;
    scale: number;
    rootOffset: UseElementBoundingReturn;
    readonly?: boolean;
}>();

const emit = defineEmits<{
    (e: "pan-by", position: { x: number; y: number }): void;
}>();

const cssVariables = computed(() => ({
    "--position-left": `${props.comment.position[0]}px`,
    "--position-top": `${props.comment.position[1]}px`,
    "--width": `${props.comment.size[0]}px`,
    "--height": `${props.comment.size[1]}px`,
}));

const { commentStore, undoRedoStore } = useWorkflowStores();
let lazyAction: LazyChangeDataAction | LazyChangePositionAction | LazyChangeSizeAction | null = null;

function onUpdateData(data: any) {
    if (lazyAction instanceof LazyChangeDataAction && undoRedoStore.isQueued(lazyAction)) {
        lazyAction.updateData(data);
    } else {
        lazyAction = new LazyChangeDataAction(commentStore, props.comment, data);
        undoRedoStore.applyLazyAction(lazyAction);
    }
}

function onResize(size: [number, number]) {
    if (lazyAction instanceof LazyChangeSizeAction && undoRedoStore.isQueued(lazyAction)) {
        lazyAction.updateData(size);
    } else {
        lazyAction = new LazyChangeSizeAction(commentStore, props.comment, size);
        undoRedoStore.applyLazyAction(lazyAction);
    }
}

function onMove(position: [number, number]) {
    if (lazyAction instanceof LazyChangePositionAction && undoRedoStore.isQueued(lazyAction)) {
        lazyAction.updateData(position);
    } else {
        lazyAction = new LazyChangePositionAction(commentStore, props.comment, position);
        undoRedoStore.applyLazyAction(lazyAction);
    }
    hasMoved = true;
}

function onPan(position: { x: number; y: number }) {
    emit("pan-by", position);
}

function onRemove() {
    undoRedoStore.applyAction(new DeleteCommentAction(commentStore, props.comment));
}

function onSetColor(color: WorkflowCommentColor) {
    undoRedoStore.applyAction(new ChangeColorAction(commentStore, props.comment, color));
}

const { deselectAll } = useMultiSelect();
let hasMoved = false;

function toggleSelect(e: MouseEvent) {
    if (!props.readonly && !(props.comment.type === "freehand") && !hasMoved) {
        if (e.shiftKey) {
            e.preventDefault();
            e.stopImmediatePropagation();
            commentStore.toggleCommentMultiSelected(props.comment.id);
        } else {
            deselectAll();
        }
    }

    hasMoved = false;
}
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
    <div class="workflow-editor-comment" :style="cssVariables" @click.capture="toggleSelect">
        <TextComment
            v-if="props.comment.type === 'text'"
            :comment="props.comment"
            :scale="props.scale"
            :readonly="props.readonly"
            :root-offset="props.rootOffset"
            @change="onUpdateData"
            @resize="onResize"
            @move="onMove"
            @pan-by="onPan"
            @remove="onRemove"
            @set-color="onSetColor" />
        <MarkdownComment
            v-else-if="props.comment.type === 'markdown'"
            :comment="props.comment"
            :scale="props.scale"
            :readonly="props.readonly"
            :root-offset="props.rootOffset"
            @change="onUpdateData"
            @resize="onResize"
            @move="onMove"
            @pan-by="onPan"
            @remove="onRemove"
            @set-color="onSetColor" />
        <FrameComment
            v-else-if="props.comment.type === 'frame'"
            :comment="props.comment"
            :scale="props.scale"
            :readonly="props.readonly"
            :root-offset="props.rootOffset"
            @change="onUpdateData"
            @resize="onResize"
            @move="onMove"
            @pan-by="onPan"
            @remove="onRemove"
            @set-color="onSetColor" />
        <FreehandComment v-else-if="props.comment.type === 'freehand'" :comment="props.comment" @remove="onRemove" />
    </div>
</template>

<style scoped lang="scss">
.workflow-editor-comment {
    position: absolute;
    width: var(--width);
    height: var(--height);
    top: var(--position-top);
    left: var(--position-left);
}
</style>
