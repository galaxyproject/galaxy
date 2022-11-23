<script setup>
import { computed, defineProps, defineEmits } from "vue";

const $emit = defineEmits(["input"]);
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
        $emit("input", val);
    },
});
</script>

<template>
    <b-form-checkbox-group
        v-model="currentValue"
        v-for="(option, index) in options" 
        :key="index" 
        :value="option[1]"
        :options="formattedOptions"
        value-field="value"
        :text-field="option[0]"
        stacked>
    </b-form-checkbox-group>
</template>
