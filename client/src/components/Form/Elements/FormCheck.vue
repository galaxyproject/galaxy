<script setup lang="ts">
import { computed } from "vue";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GCheckboxGroup from "@/components/BaseComponents/GCheckboxGroup.vue";

interface CheckOption {
    label: string;
    value: string;
}

export interface FormCheckProps {
    modelValue?: string | string[];
    options: Array<CheckOption>;
    /** Id of the element that names the option group, e.g. the parameter title */
    ariaLabelledby?: string;
}

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

const props = defineProps<FormCheckProps>();

const emit = defineEmits<{
    (e: "update:modelValue", value: string[] | null): void;
}>();

const currentValue = computed({
    get: () => {
        const val = props.modelValue ?? [];
        return Array.isArray(val) ? val : [val];
    },
    set: (newValue) => {
        if (newValue.length > 0) {
            emit("update:modelValue", newValue);
        } else {
            emit("update:modelValue", null);
        }
    },
});

const hasOptions = computed(() => props.options.length > 0);
const indeterminate = computed(() => ![0, props.options.length].includes(currentValue.value.length));
const selectAll = computed(() => currentValue.value.length === props.options.length);

function onSelectAll(selected: boolean): void {
    if (selected) {
        const allValues = props.options.map((option) => option.value);
        emit("update:modelValue", allValues);
    } else {
        emit("update:modelValue", null);
    }
}
</script>

<template>
    <div v-if="hasOptions">
        <GCheckbox
            class="mb-1"
            :model-value="selectAll"
            :indeterminate="indeterminate"
            @update:model-value="onSelectAll">
            <span v-localize>Select / Deselect all</span>
        </GCheckbox>
        <GCheckboxGroup v-model="currentValue" :aria-labelledby="props.ariaLabelledby" stacked class="pl-3">
            <GCheckbox v-for="(option, index) in options" :key="index" :value="option.value">
                {{ option.label }}
            </GCheckbox>
        </GCheckboxGroup>
    </div>
    <GAlert v-else v-localize variant="warning" show> No options available. </GAlert>
</template>
