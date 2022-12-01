<script setup>
import { computed } from "vue";
import FormCheck from "./FormCheck";
import FormRadio from "./FormRadio";

const $emit = defineEmits(["input"]);
const props = defineProps({
    value: {
        default: null,
    },
    data: {
        type: Array,
        default: null,
    },
    display: {
        type: String,
        default: null,
    },
    options: {
        type: Array,
        default: null,
    },
    multiple: {
        type: Boolean,
        default: false,
    },
});

const currentValue = computed({
    get: () => {
        return props.value;
    },
    set: (val) => {
        $emit("input", val);
    },
});

/** Provides formatted select options. */
const currentOptions = computed(() => {
    const data = props.data;
    const options = props.options;
    if (options && options.length > 0) {
        return options;
    } else if (data && data.length > 0) {
        return data.map((option) => {
            return [option.label, option.value];
        });
    }
    return [];
});
</script>

<template>
    <form-check v-if="display === 'checkboxes'" v-model="currentValue" :options="currentOptions" />
    <form-radio v-else-if="display === 'radio'" v-model="currentValue" :options="currentOptions" />
</template>
