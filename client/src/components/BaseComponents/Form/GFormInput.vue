<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
    value?: string | null;
}>();

const emit = defineEmits<{
    (e: "input", value: string | null): void;
    (e: "keydown", event: KeyboardEvent): void;
}>();

const inputValue = computed({
    get() {
        return props.value;
    },
    set(value) {
        emit("input", value ?? null);
    },
});
</script>

<template>
    <input v-model="inputValue" class="g-form-input" @keydown="(event) => emit('keydown', event)" />
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
