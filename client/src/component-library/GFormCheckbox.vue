<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
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
    <BFormCheckbox v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormCheckbox>
</template>
