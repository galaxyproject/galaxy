<script setup lang="ts">
import { BFormSelect } from "bootstrap-vue";

interface DbKey {
    id: string;
    text: string;
}

interface Props {
    /** Selected bulk dbKey value (v-model) */
    modelValue: string;
    /** Available database keys to display in dropdown */
    dbKeys: DbKey[];
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the bulk selector */
    tooltip?: string;
}

withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "Set database key for all items",
});

const emit = defineEmits<{
    (e: "update:model-value", value: string): void;
}>();

function handleInput(value: string) {
    emit("update:model-value", value);
}
</script>

<template>
    <div class="column-header-vertical">
        <span class="column-title">Reference</span>
        <BFormSelect
            v-b-tooltip.hover.noninteractive
            :value="modelValue"
            size="sm"
            :title="tooltip"
            :disabled="disabled"
            @input="handleInput">
            <option value="">Set all...</option>
            <option v-for="(dbKey, dbKeyIndex) in dbKeys" :key="dbKeyIndex" :value="dbKey.id">
                {{ dbKey.text }}
            </option>
        </BFormSelect>
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
