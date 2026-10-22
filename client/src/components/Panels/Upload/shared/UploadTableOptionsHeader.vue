<script setup lang="ts">
import type { HeaderOptionDescriptor } from "@/composables/upload/uploadOptionBindings";
import type { UploadOptionKey } from "@/composables/upload/uploadOptionModel";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

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
            <GCheckbox
                v-for="option in options"
                :key="option.key"
                v-g-tooltip.hover
                size="small"
                :indeterminate="option.indeterminate"
                :model-value="option.checked"
                :title="option.title"
                @change="handleToggle(option.key)">
                <span class="small">{{ option.label }}</span>
            </GCheckbox>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
