<script setup lang="ts">
import type { DbKey } from "@/composables/uploadConfigurations";

import SingleItemSelector from "@/components/SingleItemSelector.vue";

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

function onItemSelection(item: DbKey) {
    emit("input", item.id);
}
</script>

<template>
    <SingleItemSelector
        v-g-tooltip.hover
        collection-name="References"
        :title="tooltip"
        :items="dbKeys"
        :current-item="dbKeys.find((dbKey) => dbKey.id === value)"
        :disabled="disabled"
        @update:selected-item="onItemSelection" />
</template>
