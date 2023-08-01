<script setup lang="ts">
import { BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

const props = defineProps({
    value: {
        type: Boolean,
        default: null,
    },
    visible: {
        type: Boolean,
        default: null,
    },
});

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const model = computed({
    get: () => props.value ?? false,
    set: (value) => {
        emit("input", value);
    },
});
</script>

<template>
    <BFormRadioGroup v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormRadioGroup>
</template>
