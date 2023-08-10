<script setup lang="ts">
import { BPagination } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    value: boolean | string | number;
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
    <BPagination v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BPagination>
</template>
