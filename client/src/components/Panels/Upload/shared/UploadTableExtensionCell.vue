<script setup lang="ts">
import type { ExtensionDetails } from "@/composables/uploadConfigurations";

import SingleItemSelector from "@/components/SingleItemSelector.vue";
import UploadDatatypeWarning from "@/components/Upload/UploadDatatypeWarning.vue";

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
    <div class="w-100">
        <SingleItemSelector
            v-g-tooltip.hover
            collection-name="Data Types"
            :title="tooltip"
            :items="extensions"
            :current-item="extensions.find((ext) => ext.id === value)"
            :disabled="disabled"
            @update:selected-item="onItemSelection">
            <template v-slot:option="{ option }">
                {{ option.text }}
                <UploadDatatypeWarning :message="option.upload_warning" />
            </template>
        </SingleItemSelector>
        <div role="status">
            <UploadDatatypeWarning :message="warning" />
        </div>
    </div>
</template>
