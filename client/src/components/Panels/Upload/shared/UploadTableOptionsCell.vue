<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";

import type { RowOptionDescriptor } from "@/composables/upload/uploadOptionBindings";
import type { UploadOptionKey } from "@/composables/upload/uploadOptionModel";

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
        <BFormCheckbox
            v-for="option in options"
            :key="option.key"
            v-g-tooltip.hover
            :checked="option.checked"
            :data-test-id="getToggleTestId(option.key)"
            size="sm"
            :title="option.title"
            @change="updateOption(option.key, $event)">
            <span class="small">{{ option.label }}</span>
        </BFormCheckbox>
    </div>
</template>
