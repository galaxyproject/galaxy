<script setup lang="ts">
import { computed, type ComputedRef } from "vue";

import { useUid } from "@/composables/utils/uid";
import localize from "@/utils/localization";

import { getAllValues, type Option, type Value } from "./utilities";

import FormDrilldownList from "./FormDrilldownList.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

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
        showIcons: false,
    },
);

const emit = defineEmits<{
    (e: "input", value: Value): void;
}>();

// Unique per instance: the workflow run form can render the same parameter id once per step
const radioName = useUid(`drilldown-${props.id}-`);

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
function handleClick(clickedElement: string, value: boolean): void {
    if (props.multiple) {
        // Only the chosen option is submitted; the server expands a recurse hierarchy.
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

function setElementValues(oldArray: string[], newArray: string[], value: boolean): string[] {
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
            <GCheckbox
                v-if="multiple"
                class="select-all-checkbox"
                :indeterminate="selectAllIndeterminate"
                :model-value="selectAllChecked"
                @update:model-value="onSelectAll">
                {{ localize("Select / Deselect All") }}
            </GCheckbox>

            <FormDrilldownList
                :show-icons="showIcons"
                :multiple="multiple"
                :current-value="currentValue"
                :name="radioName"
                :options="options"
                :handle-click="handleClick" />
        </div>
        <div v-else>
            <GAlert show variant="info" class="mt-2"> No options available. </GAlert>
        </div>
    </div>
</template>
