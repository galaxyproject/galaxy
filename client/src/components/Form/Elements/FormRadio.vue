<script setup lang="ts">
import { BAlert, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    value?: string | number;
    options: {
        label: string;
        value: string | number;
    }[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string | number | undefined): void;
}>();

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
    <BAlert v-else v-localize variant="warning" show> No options available. </BAlert>
</template>
