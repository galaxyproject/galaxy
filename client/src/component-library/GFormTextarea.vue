<script setup lang="ts">
import { BFormTextarea } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    value?: string | number;
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
    <BFormTextarea v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormTextarea>
</template>
