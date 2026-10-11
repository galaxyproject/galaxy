<script setup>
import { BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

import GAlert from "@/components/BaseComponents/GAlert.vue";

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
    <BFormRadioGroup v-if="hasOptions" v-model="currentValue" stacked>
        <BFormRadio v-for="(option, index) in options" :key="index" :value="option.value">
            {{ option.label }}
        </BFormRadio>
    </BFormRadioGroup>
    <GAlert v-else v-localize variant="warning" show> No options available. </GAlert>
</template>
