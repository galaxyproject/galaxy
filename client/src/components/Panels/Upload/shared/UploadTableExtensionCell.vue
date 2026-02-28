<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ExtensionDetails } from "@/composables/uploadConfigurations";

import SingleItemSelector from "@/components/SingleItemSelector.vue";

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

function onItemSelection(value: ExtensionDetails) {
    emit("input", value.id);
}
</script>

<template>
    <div class="d-flex align-items-center w-100">
        <SingleItemSelector
            v-g-tooltip.hover.noninteractive
            class="flex-grow-1"
            collection-name="Data Types"
            :title="tooltip"
            :items="extensions"
            :current-item="extensions.find((ext) => ext.id === value)"
            :disabled="disabled"
            @update:selected-item="onItemSelection">
        </SingleItemSelector>
        <FontAwesomeIcon
            v-if="warning"
            v-g-tooltip.hover.noninteractive
            class="text-warning ml-1 flex-shrink-0"
            :icon="faExclamationTriangle"
            :title="warning" />
    </div>
</template>
