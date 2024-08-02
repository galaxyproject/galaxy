<script setup lang="ts">
import { computed, type ComputedRef } from "vue";

import { findDescendants, flattenValues, getAllValues, type Option, type Value } from "./utilities";

import FormDrilldownList from "./FormDrilldownList.vue";

const props = withDefaults(
    defineProps<{
        id: string;
        value?: Value;
        options: Array<Option>;
        multiple: boolean;
        showIcons?: boolean;
    }>(),
    {
        value: null,
        multiple: true,
        showIcons: false,
    }
);

const emit = defineEmits<{
    (e: "input", value: Value): void;
}>();

const hasOptions = computed(() => {
    return props.options.length > 0;
});

// Determine all available values
const allValues: ComputedRef<string[]> = computed(() => {
    return getAllValues(props.options);
});

// Determine current value
const currentValue: ComputedRef<string[]> = computed(() => {
    if (props.value === null || props.value === "") {
        return [];
    } else if (Array.isArray(props.value)) {
        return props.value;
    } else {
        return [props.value];
    }
});

// Determine if select all is checked
const selectAllChecked: ComputedRef<boolean> = computed(() => {
    return allValues.value.length === currentValue.value.length;
});

// Determine if select all state undetermined
const selectAllIndeterminate: ComputedRef<boolean> = computed(() => {
    return ![0, allValues.value.length].includes(currentValue.value.length);
});

// Handle click on individual check/radio element
function handleClick(clickedElement: string, value: string): void {
    if (props.multiple) {
        const clickedElements: string[] = addDescendants(props.options, clickedElement);
        const selectedElements: string[] = setElementValues(currentValue.value, clickedElements, value);
        if (selectedElements.length === 0) {
            emit("input", null);
        } else {
            emit("input", selectedElements);
        }
    } else {
        emit("input", clickedElement);
    }
}

// Handle click on select all checkbox to either select or unselect all values
function onSelectAll(selected: boolean): void {
    emit("input", selected ? allValues.value : null);
}

// Returns the descendant values and the selected/parent value (regardless of unselected or selected)
function addDescendants(selectOptions: any[], selectedValue: string): string[] {
    const descendants: any[] | null = findDescendants(selectOptions, selectedValue);
    const allValues = flattenValues(descendants);
    allValues.unshift(selectedValue);
    return allValues;
}

function setElementValues(oldArray: string[], newArray: string[], value: string): string[] {
    if (value) {
        return Array.from(new Set([...oldArray, ...newArray]));
    } else {
        const newSet = new Set(newArray);
        return oldArray.filter((item) => !newSet.has(item));
    }
}
</script>

<template>
    <div v-if="hasOptions">
        <b-form-checkbox
            v-if="multiple"
            v-localize
            :checked="selectAllChecked"
            :indeterminate="selectAllIndeterminate"
            class="d-inline select-all-checkbox"
            @change="onSelectAll">
            Select / Deselect All
        </b-form-checkbox>
        <FormDrilldownList
            :show-icons="showIcons"
            :multiple="multiple"
            :current-value="currentValue"
            :options="options"
            :handle-click="handleClick" />
    </div>
</template>
