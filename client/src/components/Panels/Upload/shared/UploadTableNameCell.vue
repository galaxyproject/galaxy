<script setup lang="ts">
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

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

function handleInput(value: string | null) {
    emit("input", value ?? "");
}

function handleBlur() {
    emit("blur");
}
</script>

<template>
    <GFormInput
        v-g-tooltip.hover
        :model-value="value"
        size="small"
        :state="state"
        :title="tooltip"
        @update:model-value="handleInput"
        @blur="handleBlur" />
</template>
