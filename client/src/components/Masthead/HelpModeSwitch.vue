<script setup lang="ts">
import { computed } from "vue";

import { useHelpModeStatusStore } from "@/stores/helpmode/helpModeStatusStore";

const tooltip = "Enable/Disable Help Mode";
const statusStore = useHelpModeStatusStore();
const enabledStatus = computed({
    get() {
        return statusStore.helpmodestatus;
    },
    set(value: boolean) {
        statusStore.setHelpModeStatus(value);
    },
});
function toggleEnabledStatus() {
    enabledStatus.value = !enabledStatus.value;
}
</script>

<template>
    <div>
        <button
            class="help-mode-button"
            :class="{ highlight: enabledStatus }"
            :title="tooltip"
            :aria-label="tooltip"
            @click="toggleEnabledStatus"
            @keydown.enter="toggleEnabledStatus">
            <i class="fas fa-question-circle fa-lg" :class="{ highlight: enabledStatus }"> </i> Help Me
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
