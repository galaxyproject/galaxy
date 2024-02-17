<script setup lang="ts">
import type { UseElementBoundingReturn } from "@vueuse/core";
import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment, WorkflowCommentColor } from "@/stores/workflowEditorCommentStore";

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

const { commentStore } = useWorkflowStores();

function onUpdateData(data: any) {
    commentStore.changeData(props.comment.id, data);
}

function onResize(size: [number, number]) {
    commentStore.changeSize(props.comment.id, size);
}

function onMove(position: [number, number]) {
    commentStore.changePosition(props.comment.id, position);
}

function onPan(position: { x: number; y: number }) {
    emit("pan-by", position);
}

function onRemove() {
    commentStore.deleteComment(props.comment.id);
}

function onSetColor(color: WorkflowCommentColor) {
    commentStore.changeColor(props.comment.id, color);
}
</script>

<template>
    <div class="workflow-editor-comment" :style="cssVariables">
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
