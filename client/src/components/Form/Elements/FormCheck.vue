<script setup lang="ts">
import { computed } from "vue";

interface CheckOption {
    label: string;
    value: string;
}

export interface FormCheckProps {
    value?: string | string[];
    options: Array<CheckOption>;
}

const props = defineProps<FormCheckProps>();

const emit = defineEmits<{
    (e: "input", value: string[] | null): void;
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
const indeterminate = computed(() => ![0, props.options.length].includes(currentValue.value.length));
const selectAll = computed(() => currentValue.value.length === props.options.length);

function onSelectAll(selected: boolean): void {
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
        <b-form-checkbox
            v-localize
            class="mb-1"
            :checked="selectAll"
            :indeterminate="indeterminate"
            @change="onSelectAll">
            Select / Deselect all
        </b-form-checkbox>
        <b-form-checkbox-group v-model="currentValue" stacked class="pl-3">
            <b-form-checkbox v-for="(option, index) in options" :key="index" :value="option.value">
                {{ option.label }}
            </b-form-checkbox>
        </b-form-checkbox-group>
    </div>
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
