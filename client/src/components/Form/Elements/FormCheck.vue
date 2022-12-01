<script setup>
import { computed } from "vue";

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
    <b-form-checkbox-group v-model="currentValue" stacked>
        <b-form-checkbox 
            v-for="(option, index) in options" 
            :key="index" 
            :value="option[1]">
                {{ option[0] }}
        </b-form-checkbox>
    </b-form-checkbox-group>
</template>
