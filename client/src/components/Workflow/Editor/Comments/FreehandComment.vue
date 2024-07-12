<script setup lang="ts">
import { curveCatmullRom, curveLinear, line } from "d3";
import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { FreehandWorkflowComment } from "@/stores/workflowEditorCommentStore";

import { vecSubtract } from "../modules/geometry";
import { colors } from "./colors";

const props = defineProps<{
    comment: FreehandWorkflowComment;
}>();

const emit = defineEmits<{
    (e: "remove"): void;
}>();

const linear = line().curve(curveLinear);
const catmullRom = line().curve(curveCatmullRom);
const { commentStore, toolbarStore } = useWorkflowStores();

const curve = computed(() => {
    if (commentStore.isJustCreated(props.comment.id)) {
        return linear(props.comment.data.line.map((p) => vecSubtract(p, props.comment.position))) ?? undefined;
    } else {
        return catmullRom(props.comment.data.line) ?? undefined;
    }
});

const style = computed(() => {
    const style = {
        "pointer-events": toolbarStore.currentTool === "freehandEraser" ? "stroke" : "none",
        "--thickness": `${props.comment.data.thickness}px`,
    } as Record<string, string>;

    if (props.comment.color !== "none") {
        style["--color"] = colors[props.comment.color];
    }

    if (toolbarStore.inputCatcherEnabled) {
        style["cursor"] = "crosshair";
    }

    return style;
});

function onMouseOver() {
    if (toolbarStore.inputCatcherPressed) {
        emit("remove");
    }
}
function onClick() {
    if (toolbarStore.inputCatcherEnabled) {
        emit("remove");
    }
}
</script>

<template>
    <svg
        class="freehand-workflow-comment"
        :class="{ 'multi-selected': commentStore.getCommentMultiSelected(props.comment.id) }">
        <path
            class="prevent-zoom"
            :d="curve"
            :style="style"
            @mouseover="onMouseOver"
            @mousedown.prevent="onClick"></path>
    </svg>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.freehand-workflow-comment {
    --color: #{$brand-primary};
    --thickness: 5px;

    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1600;
    overflow: visible;

    fill: none;
    stroke-linecap: round;

    path {
        stroke-width: var(--thickness);
        stroke: var(--color);
    }

    pointer-events: none;

    &.multi-selected {
        border-radius: 0.25rem;
        box-shadow: 0 0 0 2px $white, 0 0 0 4px lighten($brand-info, 20%);
    }
}
</style>
