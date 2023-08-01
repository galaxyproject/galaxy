<script setup lang="ts">
import { BFormRadio } from "bootstrap-vue";
import { computed } from "vue";

const props = defineProps({
    value: {
        type: Boolean,
        default: null,
    },
});

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const model = computed({
    get: () => props.value,
    set: (value) => {
        emit("input", value);
    },
});
</script>

<template>
    <BFormRadio v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormRadio>
</template>
