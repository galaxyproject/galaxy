<script setup>
import { computed } from "vue";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GRadio from "@/components/BaseComponents/GRadio.vue";
import GRadioGroup from "@/components/BaseComponents/GRadioGroup.vue";

const emit = defineEmits(["input"]);
const props = defineProps({
    value: {
        default: null,
    },
    options: {
        type: Array,
        required: true,
    },
    /** Id of the element that names the radio group, e.g. the parameter title */
    ariaLabelledby: {
        type: String,
        default: undefined,
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
    <GRadioGroup v-if="hasOptions" v-model="currentValue" :aria-labelledby="props.ariaLabelledby" stacked>
        <GRadio v-for="(option, index) in options" :key="index" :value="option.value">
            {{ option.label }}
        </GRadio>
    </GRadioGroup>
    <GAlert v-else v-localize variant="warning" show> No options available. </GAlert>
</template>
