<script setup>
import { computed } from "vue";

import { GAlert, GFormRadio, GFormRadioGroup } from "@/component-library";

const emit = defineEmits(["input"]);
const props = defineProps({
    value: {
        default: null,
    },
    options: {
        type: Array,
        required: true,
    },
});

const currentValue = computed({
    get: () => {
        return props.value;
    },
    set: (val) => {
        emit("input", val);
    },
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});
</script>

<template>
    <GFormRadioGroup v-if="hasOptions" v-model="currentValue" stacked>
        <GFormRadio v-for="(option, index) in options" :key="index" :value="option[1]">
            {{ option[0] }}
        </GFormRadio>
    </GFormRadioGroup>
    <GAlert v-else v-localize variant="warning" show> No options available. </GAlert>
</template>
