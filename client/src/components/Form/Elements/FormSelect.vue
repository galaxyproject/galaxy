<script setup lang="ts">
import { computed, onMounted, watch, type ComputedRef } from "vue";
import Multiselect from "vue-multiselect";

type SelectValue = string | null;

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: Array<[string, string]>;
        value?: string[] | string;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
    }
);

const emit = defineEmits<{
    (e: "input", value: SelectValue | SelectValue[]): void;
}>();

/**
 * Translates input options for consumption by the
 * select component into an array of objects
 */
const formattedOptions: ComputedRef<Array<SelectOption>> = computed(() => {
    const result: Array<SelectOption> = props.options.map((option: [string, string]) => ({
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
 * Tracks selected values
 */
const selectedValues: ComputedRef<Array<SelectValue>> = computed(() => {
    return Array.isArray(props.value) ? props.value : [props.value];
});

/**
 * Tracks current value and emits changes
 */
const currentValue = computed({
    get: () =>
        formattedOptions.value.filter(
            (option: SelectOption) => option.value !== null && selectedValues.value.includes(option.value)
        ),
    set: (val: Array<SelectOption> | SelectOption): void => {
        if (Array.isArray(val)) {
            const values: SelectValue[] = val.map((v: SelectOption) => v.value);
            emit("input", values);
        } else {
            emit("input", val.value);
        }
    },
});

/**
 * Ensures that an initial value is selected for non-optional inputs
 */
function setInitialValue(): void {
    if (props.value === null && !props.optional && hasOptions.value) {
        const initialValue = formattedOptions.value[0];
        if (initialValue) {
            emit("input", initialValue.value);
        }
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
        :allow-empty="optional"
        :close-on-select="!multiple"
        :options="formattedOptions"
        :multiple="multiple"
        placeholder="Select value"
        track-by="value"
        label="label" />
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
