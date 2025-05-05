<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { WorkflowInput } from "../Workflow/Editor/modules/inputs";

import ActivityPanel from "./ActivityPanel.vue";

const props = defineProps<{
    inputs: WorkflowInput[];
}>();

const emit = defineEmits<{
    (e: "insertModule", id: string, name: string, state: WorkflowInput["stateOverwrites"]): void;
}>();
</script>

<template>
    <ActivityPanel title="Inputs">
        <div class="input-list">
            <button
                v-for="(input, index) in props.inputs"
                :key="index"
                :data-id="input.id ?? input.moduleId"
                class="workflow-input-button"
                @click="emit('insertModule', input.moduleId, input.title, input.stateOverwrites)">
                <FontAwesomeIcon class="input-icon" fixed-width :icon="input.icon" />
                <span class="input-title"> {{ input.title }} </span>
                <span class="input-description"> {{ input.description }} </span>
            </button>
        </div>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.input-list {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.workflow-input-button {
    border-radius: 0.5rem;
    border: 1px solid $gray-300;
    background: transparent;

    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-areas:
        "i t"
        "d d";

    text-align: left;
    gap: 0.25rem;
    align-items: center;

    &:hover,
    &:focus {
        background-color: $gray-100;
        border-color: $brand-primary;
    }

    &:active {
        background-color: $gray-200;
        border-color: $brand-primary;
    }

    .input-icon {
        grid-area: i;
    }

    .input-title {
        grid-area: t;
        font-weight: bold;
    }

    .input-description {
        grid-area: d;
    }
}
</style>
