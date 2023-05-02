<script setup>
import { computed, onMounted, watch } from "vue";
import Multiselect from "vue-multiselect";

const emit = defineEmits(["input"]);
const props = defineProps({
    value: {
        default: null,
    },
    multiple: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array,
        required: true,
    },
    optional: {
        type: Boolean,
        default: false,
    },
});

/**
 * Translates input options for consumption by the
 * select component into an array of objects
 */
const formattedOptions = computed(() => {
    const result = props.options.map((option) => ({
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
const hasOptions = computed(() => {
    return formattedOptions.value.length > 0;
});

/**
 * Tracks selected values
 */
const selectedValues = computed(() => {
    return Array.isArray(props.value) ? props.value : [props.value];
});

/**
 * Tracks current value and emits changes
 */
const currentValue = computed({
    get: () => {
        return formattedOptions.value.filter((option) => selectedValues.value.includes(option.value));
    },
    set: (val) => {
        if (props.multiple) {
            const values = val.map((v) => v.value);
            emit("input", values);
        } else {
            emit("input", val.value);
        }
    },
});

/**
 * Ensures that an initial value is selected for non-optional inputs
 */
function setInitialValue() {
    if (props.value === null && !props.optional && hasOptions.value) {
        const initialValue = formattedOptions.value[0];
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
        :allow-empty="optional"
        :close-on-select="!multiple"
        :options="formattedOptions"
        :multiple="multiple"
        placeholder="Select value"
        track-by="value"
        label="label" />
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
