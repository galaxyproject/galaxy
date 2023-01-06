<script setup lang="ts">
import { computed } from "vue";

export interface FormBooleanProps {
    value: boolean | string;
}

const props = defineProps<FormBooleanProps>();
const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const currentValue = computed({
    get() {
        return String(props.value).toLowerCase() === "true";
    },
    set(newValue) {
        emit("input", newValue);
    },
});

const label = computed(() => (currentValue.value ? "Yes" : "No"));
</script>

<template>
    <b-form-checkbox v-model="currentValue" class="no-highlight" switch>
        {{ label }}
    </b-form-checkbox>
</template>
