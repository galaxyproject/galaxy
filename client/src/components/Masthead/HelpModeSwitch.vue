<script setup lang="ts">
import { storeToRefs } from "pinia";

import { useHelpModeStatusStore } from "@/stores/helpmode/helpModeStatusStore";

const tooltip = "Enable/Disable Help Mode";
const { status } = storeToRefs(useHelpModeStatusStore());
function toggleEnabledStatus() {
    status.value = !status.value;
}
</script>

<template>
    <div>
        <button
            class="help-mode-button"
            :class="{ highlight: status }"
            :title="tooltip"
            :aria-label="tooltip"
            @click="toggleEnabledStatus"
            @keydown.enter="toggleEnabledStatus">
            <i class="fas fa-question-circle fa-lg" :class="{ highlight: status }"> </i> Help Me
        </button>
    </div>
</template>

<style scoped>
.highlight {
    color: yellow;
}
.help-mode-button {
    background-color: inherit;
    border: 0px transparent;
    cursor: pointer;
    color: inherit;
    outline: none;
}
.help-mode-button.highlight {
    color: yellow;
}
</style>
