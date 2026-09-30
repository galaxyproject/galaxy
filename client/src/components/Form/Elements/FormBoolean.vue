<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed } from "vue";

export interface FormBooleanProps {
    value?: boolean | string | null;
    noLabel?: boolean;
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
    <BFormCheckbox v-model="currentValue" class="no-highlight" switch>
        <span v-if="!props.noLabel" v-localize>{{ label }}</span>
    </BFormCheckbox>
</template>
