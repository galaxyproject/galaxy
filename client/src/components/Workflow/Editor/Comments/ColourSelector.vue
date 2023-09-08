<script setup lang="ts">
import type { WorkflowCommentColour } from "@/stores/workflowEditorCommentStore";

import { brightColours, colours } from "./colours";

const props = defineProps<{
    colour: WorkflowCommentColour;
}>();

const emit = defineEmits<{
    (e: "set-colour", colour: WorkflowCommentColour): void;
}>();

function onClickColour(colour: WorkflowCommentColour) {
    emit("set-colour", colour);
}
</script>

<template>
    <div class="annotation-colour-selector">
        <button
            class="colour-button prevent-zoom"
            title="No Colour"
            :class="{ selected: props.colour === 'none' }"
            @click="() => onClickColour('none')"></button>
        <button
            v-for="(hex, name) in colours"
            :key="name"
            class="colour-button prevent-zoom"
            :title="`Colour ${name}`"
            :class="{ selected: props.colour === name }"
            :style="{
                '--colour': hex,
                '--colour-bright': brightColours[name],
            }"
            @click="() => onClickColour(name)"></button>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.annotation-colour-selector {
    position: absolute;

    display: grid;
    grid-template-rows: 1rem 1rem;
    grid-template-columns: repeat(5, 1rem);
    grid-auto-flow: column;

    overflow: hidden;
    border-radius: 0.25rem;

    .colour-button {
        --colour: #{$brand-primary};
        --colour-bright: #{$brand-secondary};

        background-color: var(--colour);
        border-color: var(--colour-bright);
        border-width: 0;
        border-radius: 0;
        padding: 0;

        width: 100%;
        height: 100%;

        display: grid;
        place-items: center;

        transition: none;

        &:hover {
            background-color: var(--colour-bright);
        }

        &:focus,
        &:focus-visible {
            border-color: var(--colour-bright);
            border-width: 2px;
            box-shadow: none;
        }

        &.selected::after {
            content: "";
            display: block;
            width: 50%;
            height: 50%;
            border-radius: 50%;
            background-color: var(--colour-bright);
        }

        &.selected:hover::after {
            background-color: var(--colour);
        }
    }
}
</style>
