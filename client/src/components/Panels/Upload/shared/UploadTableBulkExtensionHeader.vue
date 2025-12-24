<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormSelect } from "bootstrap-vue";

import type { ExtensionDetails } from "@/composables/uploadConfigurations";

interface Props {
    /** Selected bulk extension value */
    value: string;
    /** Available extensions to display in dropdown */
    extensions: ExtensionDetails[];
    /** Warning message for current bulk selection */
    warning?: string;
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the bulk selector */
    tooltip?: string;
}

withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "Set file format for all items",
    warning: undefined,
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

function handleInput(value: string) {
    emit("input", value);
}
</script>

<template>
    <div class="column-header-vertical">
        <span class="column-title">Type</span>
        <BFormSelect
            v-b-tooltip.hover.noninteractive
            :value="value"
            size="sm"
            :title="tooltip"
            :disabled="disabled"
            @input="handleInput">
            <option value="">Set all...</option>
            <option v-for="(ext, extIndex) in extensions" :key="extIndex" :value="ext.id">
                {{ ext.text }}
            </option>
        </BFormSelect>
        <FontAwesomeIcon
            v-if="warning"
            v-b-tooltip.hover.noninteractive
            class="text-warning warning-icon"
            :icon="faExclamationTriangle"
            :title="warning" />
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
