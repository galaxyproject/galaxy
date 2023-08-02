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
</script>

<template>
    <div>
        <b-form-checkbox v-model="enabledStatus" class="no-highlight" switch :title="tooltip"> </b-form-checkbox>
    </div>
</template>
