<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed } from "vue";

export interface Props {
    value: boolean | "true" | "false";
}

const props = defineProps<Props>();

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
    <BFormCheckbox v-model="currentValue" class="no-highlight" switch>
        {{ label }}
    </BFormCheckbox>
</template>
