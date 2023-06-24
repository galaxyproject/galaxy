<script setup lang="ts">
import { computed, onMounted, watch, type ComputedRef } from "vue";
import Multiselect from "vue-multiselect";
import { useMultiselect } from "@/composables/useMultiselect";

type SelectValue = string | number | null;
const { ariaExpanded, onOpen, onClose } = useMultiselect();

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: Array<[string, SelectValue]>;
        value?: Array<SelectValue> | string | number;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
    }
);

const emit = defineEmits<{
    (e: "input", value: SelectValue | Array<SelectValue>): void;
}>();

/**
 * Determine dom wrapper class
 */
const cls: ComputedRef<string> = computed(() => {
    return props.multiple ? "form-select-multiple" : "form-select-single";
});

/**
 * Configure deselect label
 */
const deselectLabel: ComputedRef<string> = computed(() => {
    return props.multiple ? "Click to remove" : "";
});

/**
 * Translates input options for consumption by the
 * select component into an array of objects
 */
const formattedOptions: ComputedRef<Array<SelectOption>> = computed(() => {
    const result: Array<SelectOption> = props.options.map((option) => ({
        label: option[0],
        value: option[1],
    }));
    if (props.optional && !props.multiple) {
        result.unshift({
            label: "Nothing selected",
            value: null,
        });
    }
    return result;
});

/**
 * Tracks if the select field has options
 */
const hasOptions: ComputedRef<Boolean> = computed(() => {
    return formattedOptions.value.length > 0;
});

/**
 * Provides initial value if necessary
 */
const initialValue: ComputedRef<SelectValue> = computed(() => {
    if (props.value === null && !props.optional && hasOptions.value) {
        const v = formattedOptions.value[0];
        if (v) {
            return v.value;
        }
    }
    return null;
});

/**
 * Configure selected label
 */
const selectedLabel: ComputedRef<string> = computed(() => {
    return props.multiple ? "Selected" : "";
});

/**
 * Tracks selected values
 */
const selectedValues: ComputedRef<Array<SelectValue>> = computed(() => {
    return Array.isArray(props.value) ? props.value : [props.value];
});

/**
 * Tracks current value and emits changes
 */
const currentValue = computed({
    get: () => formattedOptions.value.filter((option: SelectOption) => selectedValues.value.includes(option.value)),
    set: (val: Array<SelectOption> | SelectOption): void => {
        if (Array.isArray(val)) {
            if (val.length > 0) {
                const values: Array<SelectValue> = val.map((v: SelectOption) => v.value);
                emit("input", values);
            } else {
                emit("input", null);
            }
        } else {
            emit("input", val ? val.value : null);
        }
    },
});

/**
 * Ensures that an initial value is selected for non-optional inputs
 */
function setInitialValue(): void {
    if (initialValue.value) {
        emit("input", initialValue.value);
    }
}

/**
 * Watches changes in select options and adjusts initial value if necessary
 */
watch(
    () => props.options,
    () => setInitialValue()
);

/**
 * Sets initial value if necessary
 */
onMounted(() => {
    setInitialValue();
});
</script>

<template>
    <multiselect
        v-if="hasOptions"
        v-model="currentValue"
        :allow-empty="true"
        :class="['form-select', cls]"
        :close-on-select="!multiple"
        :deselect-label="deselectLabel"
        :options="formattedOptions"
        :multiple="multiple"
        :selected-label="selectedLabel"
        :aria-expanded="ariaExpanded"
        placeholder="Select value"
        select-label="Click to select"
        track-by="value"
        label="label"
        @open="onOpen"
        @close="onClose" />
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
