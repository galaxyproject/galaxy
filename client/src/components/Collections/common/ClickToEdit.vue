<script setup lang="ts">
import { ref, watch } from "vue";

interface Props {
    value: string;
    title?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const editable = ref(false);
const localValue = ref(props.value);

watch(
    () => localValue.value,
    (newLocalValue) => {
        emit("input", newLocalValue);
    }
);

watch(
    () => props.value,
    (newValue) => {
        localValue.value = newValue;
    }
);
</script>

<template>
    <input
        v-if="editable"
        v-model="localValue"
        class="click-to-edit-input"
        contenteditable
        @blur="editable = false"
        @keyup.enter="editable = false" />

    <label v-else @click="editable = true">
        {{ localValue }}
    </label>
</template>

<style scoped lang="scss">
.click-to-edit-input {
    width: 600px;
    line-height: 1 !important;
}
</style>
