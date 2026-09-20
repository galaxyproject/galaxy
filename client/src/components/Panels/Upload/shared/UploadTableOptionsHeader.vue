<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";

import type { HeaderOptionDescriptor } from "@/composables/upload/uploadOptionBindings";
import type { UploadOptionKey } from "@/composables/upload/uploadOptionModel";

interface Props {
    /** Bulk option descriptors to render in order */
    options: HeaderOptionDescriptor[];
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "toggle", key: UploadOptionKey): void;
}>();

function handleToggle(key: UploadOptionKey) {
    emit("toggle", key);
}
</script>

<template>
    <div class="options-header">
        <span class="options-title">Upload Settings</span>
        <div class="options-controls d-inline-flex align-items-center flex-nowrap">
            <BFormCheckbox
                v-for="option in options"
                :key="option.key"
                v-g-tooltip.hover
                :checked="option.checked"
                :indeterminate="option.indeterminate"
                size="sm"
                :title="option.title"
                @change="handleToggle(option.key)">
                <span class="small">{{ option.label }}</span>
            </BFormCheckbox>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
