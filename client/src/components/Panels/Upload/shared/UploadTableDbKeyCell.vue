<script setup lang="ts">
import { BFormSelect } from "bootstrap-vue";

import type { DbKey } from "@/composables/uploadConfigurations";

interface Props {
    /** Currently selected database key for this item */
    value: string;
    /** Available database keys to display in dropdown */
    dbKeys: DbKey[];
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the selector */
    tooltip?: string;
}

withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "Database key for this dataset",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

function handleInput(value: string) {
    emit("input", value);
}
</script>

<template>
    <BFormSelect
        v-b-tooltip.hover.noninteractive
        :value="value"
        size="sm"
        :title="tooltip"
        :disabled="disabled"
        @input="handleInput">
        <option v-for="(dbKey, dbKeyIndex) in dbKeys" :key="dbKeyIndex" :value="dbKey.id">
            {{ dbKey.text }}
        </option>
    </BFormSelect>
</template>
