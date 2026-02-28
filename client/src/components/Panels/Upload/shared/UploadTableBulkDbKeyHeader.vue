<script setup lang="ts">
import { computed } from "vue";

import type { DbKey } from "@/composables/uploadConfigurations";

import SingleItemSelector from "@/components/SingleItemSelector.vue";

interface Props {
    /** Selected bulk dbKey value */
    value: string;
    /** Available database keys to display in dropdown */
    dbKeys: DbKey[];
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the bulk selector */
    tooltip?: string;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "Set database key for all items",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const optionsWithDefault = computed(() => [{ id: "", text: "Set all..." }, ...(props.dbKeys || [])]);

function onItemSelection(item: DbKey) {
    emit("input", item.id);
}
</script>

<template>
    <div class="column-header-vertical">
        <span class="column-title">Reference</span>
        <SingleItemSelector
            v-g-tooltip.hover.noninteractive
            class="w-100"
            collection-name="References"
            :title="tooltip"
            :items="optionsWithDefault"
            :current-item="props.dbKeys.find((dbKey) => dbKey.id === props.value) || optionsWithDefault[0]"
            :disabled="disabled"
            @update:selected-item="onItemSelection" />
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
