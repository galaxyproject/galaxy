<script setup lang="ts">
import { computed } from "vue";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

export interface FormBooleanProps {
    modelValue?: boolean | string | null;
    noLabel?: boolean;
}

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

const props = defineProps<FormBooleanProps>();
const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
}>();

const currentValue = computed({
    get() {
        return String(props.modelValue).toLowerCase() === "true";
    },
    set(newValue) {
        emit("update:modelValue", newValue);
    },
});

const label = computed(() => (currentValue.value ? "Yes" : "No"));
</script>

<template>
    <GCheckbox v-model="currentValue" class="no-highlight" switch>
        <!-- No slot at all without a label, so GCheckbox renders no empty label span -->
        <template v-if="!props.noLabel" v-slot>
            <span v-localize>{{ label }}</span>
        </template>
    </GCheckbox>
</template>
