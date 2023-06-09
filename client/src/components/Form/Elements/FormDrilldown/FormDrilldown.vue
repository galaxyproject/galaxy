<script setup lang="ts">
import { computed, type ComputedRef } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import { getAllValues, type Option, type Value } from "./utilities";

const props = withDefaults(
    defineProps<{
        id: string;
        value?: Value;
        options: Array<Option>;
        multiple: boolean;
    }>(),
    {
        value: null,
        multiple: true,
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
function handleClick(value: string): void {
    if (props.multiple) {
        const newValue: string[] = currentValue.value.slice();
        const index: number = newValue.indexOf(value);
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
        <form-drilldown-list
            :multiple="multiple"
            :current-value="currentValue"
            :options="options"
            :handle-click="handleClick" />
    </div>
</template>
