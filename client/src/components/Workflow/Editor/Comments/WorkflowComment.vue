<script setup lang="ts">
import { computed } from "vue";

import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";

import FrameComment from "./FrameComment.vue";
import FreehandComment from "./FreehandComment.vue";
import MarkdownComment from "./MarkdownComment.vue";
import TextComment from "./TextComment.vue";

const props = defineProps<{
    comment: WorkflowComment;
}>();

const cssVariables = computed(() => ({
    "--position-left": `${props.comment.position[0]}px`,
    "--position-top": `${props.comment.position[1]}px`,
    "--width": `${props.comment.size[0]}px`,
    "--height": `${props.comment.size[1]}px`,
}));
</script>

<template>
    <div class="workflow-editor-comment" :style="cssVariables">
        <TextComment v-if="props.comment.type === 'text'" />
        <MarkdownComment v-else-if="props.comment.type === 'markdown'" />
        <FrameComment v-else-if="props.comment.type === 'frame'" />
        <FreehandComment v-else-if="props.comment.type === 'freehand'" />
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
