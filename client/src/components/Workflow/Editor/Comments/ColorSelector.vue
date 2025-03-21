<script setup lang="ts">
import type { WorkflowCommentColor } from "@/stores/workflowEditorCommentStore";

import { brightColors, colors } from "./colors";

const props = defineProps<{
    color: WorkflowCommentColor;
}>();

const emit = defineEmits<{
    (e: "set-color", color: WorkflowCommentColor): void;
}>();

function onClickColor(color: WorkflowCommentColor) {
    emit("set-color", color);
}
</script>

<template>
    <div class="comment-color-selector">
        <button
            class="color-button prevent-zoom"
            title="无颜色"
            data-color="none"
            :class="{ selected: props.color === 'none' }"
            @click="() => onClickColor('none')"></button>
        <button
            v-for="(hex, name) in colors"
            :key="name"
            class="color-button prevent-zoom"
            :data-color="name"
            :title="`颜色 ${name}`"
            :class="{ selected: props.color === name }"
            :style="{
                '--color': hex,
                '--color-bright': brightColors[name],
            }"
            @click="() => onClickColor(name)"></button>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.comment-color-selector {
    position: absolute;
    z-index: 10000;

    display: grid;
    grid-template-rows: 1rem 1rem;
    grid-template-columns: repeat(5, 1rem);
    grid-auto-flow: column;

    overflow: hidden;
    border-radius: 0.25rem;

    .color-button {
        --color: #{$brand-primary};
        --color-bright: #{$brand-secondary};

        background-color: var(--color);
        border-color: var(--color-bright);
        border-width: 0;
        border-radius: 0;
        padding: 0;

        width: 100%;
        height: 100%;

        display: grid;
        place-items: center;

        transition: none;

        &:hover {
            background-color: var(--color-bright);
        }

        &:focus,
        &:focus-visible {
            border-color: var(--color-bright);
            border-width: 2px;
            box-shadow: none;
        }

        &.selected::after {
            content: "";
            display: block;
            width: 50%;
            height: 50%;
            border-radius: 50%;
            background-color: var(--color-bright);
        }

        &.selected:hover::after {
            background-color: var(--color);
        }
    }
}
</style>
