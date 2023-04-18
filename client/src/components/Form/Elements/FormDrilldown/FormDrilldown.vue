<script setup lang="ts">
import { computed, ref, type ComputedRef } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./types.js";

export interface FormDrilldownProps {
    id: string;
    value?: string | string[];
    options: Array<Option>;
    multiple: boolean;
}

const props = withDefaults(defineProps<FormDrilldownProps>(), {
    value: null,
    multiple: true,
});

const emit = defineEmits<{
    (e: "input", value: string | string[] | null): void;
}>();

const selectAllIndeterminate = ref(false);
const selectAll = ref(false);

const hasOptions = computed(() => {
    return props.options.length > 0;
});

// Determine all available values
const allValues: ComputedRef<string[]> = computed(() => {
    let options = null;
    const values: string[] = [];
    const stack: Array<Array<Option>> = [props.options];
    while ((options = stack.pop())) {
        options.forEach((option) => {
            if (option.value) {
                values.push(option.value);
            }
            if (option.options.length > 0) {
                stack.push(option.options);
            }
        });
    }
    return values;
});

// Determine current value and set select all state
const currentValue = computed({
    get: (): string[] => {
        // determine current value
        let value: string[] = [];
        if (props.value !== null && props.value !== "") {
            if (Array.isArray(props.value)) {
                value = props.value;
            } else {
                value = [props.value];
            }
        }
        // set select all state
        selectAll.value = allValues.value.length === value.length;
        selectAllIndeterminate.value = ![0, allValues.value.length].includes(value.length);
        // return current value
        return value;
    },
    set: (newValue: string[]): void => {
        emit("input", newValue);
    },
});

// Handle click on individual check/radio element
function handleClick(value: string): void {
    if (props.multiple) {
        const newValue = currentValue.value.slice();
        const index = newValue.indexOf(value);
        if (index !== -1) {
            newValue.splice(index, 1);
        } else {
            newValue.push(value);
        }
        if (newValue.length === 0) {
            emit("input", null);
        } else {
            emit("input", newValue);
        }
    } else {
        emit("input", value);
    }
}

// Handle click on select all checkbox to either select or unselect all values
function onSelectAll(selected: boolean): void {
    emit("input", selected ? allValues.value : null);
    selectAll.value = selected;
    selectAllIndeterminate.value = false;
}
</script>

<template>
    <div v-if="hasOptions">
        <b-form-checkbox
            v-if="props.multiple"
            v-model="selectAll"
            :indeterminate="selectAllIndeterminate"
            class="d-inline select-all-checkbox"
            @change="onSelectAll" />
        Select/Deselect All
        <form-drilldown-list
            :multiple="props.multiple"
            :current-value="currentValue"
            :options="options"
            :handle-click="handleClick" />
    </div>
</template>
