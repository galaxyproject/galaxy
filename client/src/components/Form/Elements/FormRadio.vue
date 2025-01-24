<script setup>
import { computed } from "vue";

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
    <b-form-radio-group v-if="hasOptions" v-model="currentValue" stacked>
        <b-form-radio v-for="(option, index) in options" :key="index" :value="option.value">
            {{ option.label }}
        </b-form-radio>
    </b-form-radio-group>
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
