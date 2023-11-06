<script setup>
import { computed } from "vue";

import FormCheck from "./FormCheck.vue";
import FormRadio from "./FormRadio.vue";
import FormSelect from "./FormSelect.vue";

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
    optional: {
        type: Boolean,
        default: false,
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
    let result = [];
    const data = props.data;
    const options = props.options;
    if (options && options.length > 0) {
        result = options.map((option) => ({ label: option[0], value: option[1] }));
    } else if (data && data.length > 0) {
        result = data;
    }
    if (!props.display && !props.multiple && props.optional) {
        result.unshift({
            label: "Nothing selected",
            value: null,
        });
    }
    return result;
});
</script>

<template>
    <FormCheck v-if="display === 'checkboxes'" v-model="currentValue" :options="currentOptions" />
    <FormRadio v-else-if="display === 'radio'" v-model="currentValue" :options="currentOptions" />
    <FormSelect v-else v-model="currentValue" :multiple="multiple" :optional="optional" :options="currentOptions" />
</template>
