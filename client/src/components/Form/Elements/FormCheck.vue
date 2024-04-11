<script setup lang="ts">
import { BAlert, BFormCheckbox, BFormCheckboxGroup } from "bootstrap-vue";
import { computed } from "vue";

type Value = string | number | boolean;

interface CheckOption {
    label: string;
    value: Value;
}

export interface Props {
    options: CheckOption[];
    value?: Value | Value[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Value | Value[] | null): void;
}>();

const currentValue = computed({
    get: () => {
        const val = props.value ?? [];

        return Array.isArray(val) ? val : [val];
    },
    set: (newValue) => {
        if (newValue.length > 0) {
            emit("input", newValue);
        } else {
            emit("input", null);
        }
    },
});

const hasOptions = computed(() => props.options.length > 0);
const selectAll = computed(() => currentValue.value.length === props.options.length);
const indeterminate = computed(() => ![0, props.options.length].includes(currentValue.value.length));

function onSelectAll(selected: boolean) {
    if (selected) {
        const allValues = props.options.map((option) => option.value);

        emit("input", allValues);
    } else {
        emit("input", null);
    }
}
</script>

<template>
    <div v-if="hasOptions">
        <BFormCheckbox
            v-localize
            class="mb-1"
            :checked="selectAll"
            :indeterminate="indeterminate"
            @change="onSelectAll">
            Select / Deselect all
        </BFormCheckbox>

        <BFormCheckboxGroup v-model="currentValue" stacked class="pl-3">
            <BFormCheckbox v-for="(option, index) in options" :key="index" :value="option.value">
                {{ option.label }}
            </BFormCheckbox>
        </BFormCheckboxGroup>
    </div>
    <BAlert v-else v-localize variant="warning" show> No options available. </BAlert>
</template>
