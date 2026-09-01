<script setup lang="ts">
import { BAlert, BFormCheckbox } from "bootstrap-vue";
import { computed, type ComputedRef } from "vue";

import { getAllValues, type Option, type Value } from "./utilities";

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
    },
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
        // Only the chosen option is submitted; the server expands a recurse hierarchy.
        // Covered by FormDrilldown.test.js and the drill_down tool tests.
        const selectedElements: string[] = setElementValues(currentValue.value, [clickedElement], value);
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
    <div>
        <div v-if="hasOptions">
            <BFormCheckbox
                v-if="multiple"
                v-localize
                :checked="selectAllChecked"
                :indeterminate="selectAllIndeterminate"
                class="d-inline select-all-checkbox"
                @change="onSelectAll">
                Select / Deselect All
            </BFormCheckbox>

            <FormDrilldownList
                :show-icons="showIcons"
                :multiple="multiple"
                :current-value="currentValue"
                :options="options"
                :handle-click="handleClick" />
        </div>
        <div v-else>
            <BAlert show variant="info" class="mt-2"> No options available. </BAlert>
        </div>
    </div>
</template>
