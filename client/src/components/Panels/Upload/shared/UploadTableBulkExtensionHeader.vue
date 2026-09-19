<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ExtensionDetails } from "@/composables/uploadConfigurations";

import SingleItemSelector from "@/components/SingleItemSelector.vue";

interface Props {
    /** Selected bulk extension value */
    value: string;
    /** Available extensions to display in dropdown */
    extensions: ExtensionDetails[];
    /** Warning message for current bulk selection */
    warning?: string;
    /** Whether the dropdown should be disabled */
    disabled?: boolean;
    /** Tooltip text for the bulk selector */
    tooltip?: string;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    tooltip: "Set file format for all items",
    warning: undefined,
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const optionsWithDefault = computed(() => [{ id: "", text: "Set all..." }, ...(props.extensions || [])]);

function onItemSelection(item: ExtensionDetails) {
    emit("input", item.id);
}
</script>

<template>
    <div class="column-header-vertical">
        <span class="column-title">Type</span>
        <SingleItemSelector
            v-g-tooltip.hover
            collection-name="Data Types"
            :title="tooltip"
            :items="optionsWithDefault"
            :current-item="props.extensions.find((e) => e.id === props.value) || optionsWithDefault[0]"
            :disabled="disabled"
            @update:selected-item="onItemSelection" />
        <FontAwesomeIcon
            v-if="warning"
            v-g-tooltip.hover
            class="text-warning warning-icon"
            :icon="faExclamationTriangle"
            :title="warning" />
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
