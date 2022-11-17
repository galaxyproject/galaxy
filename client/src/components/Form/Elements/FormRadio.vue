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
    <b-form-radio-group v-model="currentValue" stacked>
        <b-form-radio v-for="(option, index) in options" :key="index" :value="option[1]">
            {{ option[0] }}
        </b-form-radio>
    </b-form-radio-group>
</template>
