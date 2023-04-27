<script setup>
import { computed } from "vue";
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

const formattedOptions = computed(() => {
    return props.options.map((option) => ({
        label: option[0],
        value: option[1],
    }));
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});

const currentValue = computed({
    get: () => {
        if (props.value === null) {
            if (!props.optional && hasOptions) {
                const initialValue = formattedOptions.value[0];
                emit("input", initialValue.value);
                return initialValue;
            }
        } else {
            const selectedValues = Array.isArray(props.value) ? props.value : [props.value];
            return formattedOptions.value.filter((option) => selectedValues.indexOf(option.value) > -1);
        }
    },
    set: (val) => {
        emit("input", val.value);
    },
});
</script>

<template>
    <multiselect
        v-if="hasOptions"
        v-model="currentValue"
        :close-on-select="!multiple"
        :options="formattedOptions"
        :multiple="multiple"
        :allow-empty="optional"
        placeholder="Select value"
        track-by="value"
        label="label" />
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
