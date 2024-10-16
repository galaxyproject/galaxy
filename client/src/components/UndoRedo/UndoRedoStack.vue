<script setup lang="ts">
import { ref, watch } from "vue";

import { useUndoRedoStore } from "@/stores/undoRedoStore";

import ActivityPanel from "../Panels/ActivityPanel.vue";

const props = defineProps<{
    storeId: string;
}>();

const currentStore = ref(useUndoRedoStore(props.storeId));

watch(
    () => props.storeId,
    (id) => (currentStore.value = useUndoRedoStore(id))
);

function onInput(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    const valueNumber = parseFloat(value);
    const nonNanValue = isNaN(valueNumber) ? 0 : valueNumber;

    currentStore.value.savedUndoActions = nonNanValue;
    savedUndoActions.value = nonNanValue;
}

const savedUndoActions = ref(currentStore.value.savedUndoActions);

function updateSavedUndoActions() {
    savedUndoActions.value = currentStore.value.savedUndoActions;
}
</script>

<template>
    <ActivityPanel title="Latest Changes" class="undo-redo-stack">
        <div class="scroll-list">
            <button
                v-for="action in currentStore.redoActionStack"
                :key="action.id"
                class="action future"
                @click="currentStore.rollForwardTo(action)">
                {{ action.name }}
            </button>

            <span class="state-indicator"> current state </span>

            <button v-if="currentStore.pendingLazyAction" class="action lazy" @click="currentStore.undo">
                {{ currentStore.pendingLazyAction.name }}
            </button>

            <button
                v-for="action in [...currentStore.undoActionStack].reverse()"
                :key="action.id"
                class="action past"
                @click="currentStore.rollBackTo(action)">
                {{ action.name }}
            </button>

            <span v-if="currentStore.deletedActions.length !== 0" class="state-indicator"> latest saved state </span>

            <span v-for="(action, i) in [...currentStore.deletedActions].reverse()" :key="i" class="action dead">
                {{ action }}
            </span>

            <span class="state-indicator"> start of session </span>
        </div>

        <span class="info"> click an action to undo/redo multiple changes </span>

        <label>
            Max saved changes
            <input
                :value="savedUndoActions"
                type="number"
                step="1"
                :min="currentStore.minUndoActions"
                :max="currentStore.maxUndoActions"
                @input="onInput"
                @focusin="updateSavedUndoActions"
                @focusout="updateSavedUndoActions"
                @keyup.enter="updateSavedUndoActions" />
        </label>
    </ActivityPanel>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.info {
    line-height: 1;
    margin-bottom: 0.5rem;
    margin-top: 0.25rem;
    color: $text-muted;
    font-style: italic;
}

.undo-redo-stack {
    width: 100%;

    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    overflow-y: hidden;

    display: flex;
    flex-direction: column;

    .scroll-list {
        display: flex;
        flex-direction: column;
        overflow-y: auto;
        flex: 1;
    }
}

.action {
    text-align: left;
    background-color: transparent;
    border: none;
    padding: 0.1rem;
    padding-left: 0;
    line-height: 1.2;

    display: grid;
    grid-template-columns: 8px auto;
    align-items: center;
    gap: 0.5rem;

    &::before {
        content: "";
        display: block;
        height: 2px;
        background-color: $brand-secondary;
    }

    &:focus-visible {
        background-color: $brand-secondary;
    }

    &.lazy {
        color: $text-muted;
    }

    &.future {
        color: $text-light;
    }

    &.past {
        &::before {
            background-color: $text-light;
        }
    }

    &.dead {
        color: $text-light;
        &::before {
            background-color: transparent;
        }
    }
}

.state-indicator {
    display: grid;
    grid-template-columns: 1rem auto 1fr;
    gap: 0.5rem;
    align-items: center;
    color: $text-light;

    &::before,
    &::after {
        content: "";
        display: block;
        height: 2px;
        background-color: $brand-secondary;
    }
}
</style>
