<script setup lang="ts">
import type { RowOptionDescriptor } from "@/composables/upload/uploadOptionBindings";
import type { UploadOptionKey } from "@/composables/upload/uploadOptionModel";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

interface Props {
    /** Row option descriptors to render in order */
    options: RowOptionDescriptor[];
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "update", payload: { key: UploadOptionKey; value: boolean }): void;
}>();

function updateOption(key: UploadOptionKey, value: boolean) {
    emit("update", { key, value });
}

function getToggleTestId(key: UploadOptionKey): string | undefined {
    if (key === "deferred") {
        return "deferred-toggle";
    }

    if (key === "autoDecompress") {
        return "auto-decompress-toggle";
    }

    return undefined;
}
</script>

<template>
    <div class="options-cell options-controls d-inline-flex align-items-center flex-nowrap">
        <GCheckbox
            v-for="option in options"
            :key="option.key"
            v-g-tooltip.hover
            size="small"
            :data-test-id="getToggleTestId(option.key)"
            :model-value="option.checked"
            :title="option.title"
            @update:model-value="updateOption(option.key, $event)">
            <span class="small">{{ option.label }}</span>
        </GCheckbox>
    </div>
</template>
