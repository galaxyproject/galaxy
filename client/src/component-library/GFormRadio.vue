<script setup lang="ts">
import { BFormRadio } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    value: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["value"]): void;
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
