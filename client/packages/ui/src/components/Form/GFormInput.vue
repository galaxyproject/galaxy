<script setup lang="ts">
import { computed, ref } from "vue";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

const props = defineProps<{
    modelValue?: string | null;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: string | null): void;
    (e: "keydown", event: KeyboardEvent): void;
    (e: "blur", event: FocusEvent): void;
}>();

const inputElement = ref<HTMLInputElement | null>(null);

const inputValue = computed({
    get() {
        return props.modelValue;
    },
    set(value) {
        emit("update:modelValue", value ?? null);
    },
});

defineExpose({
    focus() {
        inputElement.value?.focus();
    },
    getInputElement() {
        return inputElement.value;
    },
});
</script>

<template>
    <input
        ref="inputElement"
        v-model="inputValue"
        class="g-form-input"
        @keydown="(event: KeyboardEvent) => emit('keydown', event)"
        @blur="(event: FocusEvent) => emit('blur', event)" />
</template>

<style scoped lang="scss">
.g-form-input {
    border-radius: var(--spacing-1);
    border-style: solid;
    border-width: 1px;
    border-color: var(--color-grey-400);

    color: var(--color-grey-800);

    padding: var(--spacing-1) var(--spacing-2);

    &:focus {
        outline: none;
        box-shadow: 0 0 0 0.2rem rgb(from var(--color-blue-400) r g b / 0.33);
        z-index: 999;
    }

    &:focus-visible {
        outline: none;
        box-shadow: 0 0 0 0.2rem var(--color-blue-400);
        z-index: 999;
    }
}
</style>
