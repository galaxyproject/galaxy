<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";

interface Props {
    /** Current name value */
    value: string;
    /** Validation state (true = valid, false = invalid, null = neutral) */
    state?: boolean | null;
    /** Tooltip text for the input */
    tooltip?: string;
}

withDefaults(defineProps<Props>(), {
    state: null,
    tooltip: "Dataset name in your history (required)",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
    (e: "blur"): void;
}>();

function handleInput(value: string) {
    emit("input", value);
}

function handleBlur() {
    emit("blur");
}
</script>

<template>
    <BFormInput
        v-b-tooltip.hover.noninteractive
        :value="value"
        size="sm"
        :state="state"
        :title="tooltip"
        @input="handleInput"
        @blur="handleBlur" />
</template>
