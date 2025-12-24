<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormSelect } from "bootstrap-vue";

import type { ExtensionDetails } from "@/composables/uploadConfigurations";

interface Props {
    /** Currently selected extension for this item */
    value: string;
    /** Available extensions to display in dropdown */
    extensions: ExtensionDetails[];
    /** Warning message for the current extension (if any) */
    warning?: string | null;
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the selector */
    tooltip?: string;
}

withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "File format (auto-detect recommended)",
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
    <div class="d-flex align-items-center">
        <BFormSelect
            v-b-tooltip.hover.noninteractive
            :value="value"
            size="sm"
            :title="tooltip"
            :disabled="disabled"
            @input="handleInput">
            <option v-for="(ext, extIndex) in extensions" :key="extIndex" :value="ext.id">
                {{ ext.text }}
            </option>
        </BFormSelect>
        <FontAwesomeIcon
            v-if="warning"
            v-b-tooltip.hover.noninteractive
            class="text-warning ml-1 flex-shrink-0"
            :icon="faExclamationTriangle"
            :title="warning" />
    </div>
</template>
