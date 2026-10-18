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
        type="text"
        class="g-form-input"
        @keydown="(event: KeyboardEvent) => emit('keydown', event)"
        @blur="(event: FocusEvent) => emit('blur', event)" />
</template>

<style scoped lang="scss">
// Colours stay scoped so the galaxy-ui tokens beat any field class a consumer adds
.g-form-input {
    color: var(--color-grey-800);
    border-color: var(--color-grey-400);

    &::placeholder {
        color: var(--color-grey-600);
        // Firefox lowers placeholder opacity by default
        opacity: 1;
    }

    &:disabled,
    &[readonly] {
        background-color: var(--color-grey-200);
    }

    &[type="range"] {
        background-color: transparent;
    }

    // Keep the token colours on focus when a consumer's field class sets its own
    &:focus {
        color: var(--color-grey-800);
        border-color: var(--color-grey-400);
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

<style lang="scss">
// Field box from the --field-* tokens. It sits in :where() at zero specificity, so a consumer's own
// classes and input group rules win where they apply.
:where(.g-form-input) {
    display: block;
    box-sizing: border-box;
    width: 100%;
    height: var(--field-height-medium);
    padding: var(--field-padding-y-medium) var(--field-padding-x-medium);
    background-color: var(--background-color);
    background-clip: padding-box;
    border: 1px solid;
    border-radius: var(--field-radius-medium);
    transition:
        border-color 0.15s ease-in-out,
        box-shadow 0.15s ease-in-out;

    @media (prefers-reduced-motion: reduce) {
        transition: none;
    }
}

// Font stays at class specificity: page-level font rules on input elements would beat :where()
.g-form-input {
    font-size: var(--font-size-medium);
    font-weight: 400;
    line-height: 1.5;
}

:where(.g-form-input[type="range"]) {
    width: 100%;
    height: auto;
    padding: 0;
    border: 0;
}

// Inside an input group the field flexes to fill the row and takes the group's size
:where(.input-group > .g-form-input) {
    position: relative;
    flex: 1 1 auto;
    width: 1%;
    min-width: 0;
    margin-bottom: 0;
}

:where(.input-group-sm > .g-form-input) {
    height: var(--field-height-small);
    padding: var(--field-padding-y-small) var(--field-padding-x-small);
    border-radius: var(--field-radius-small);
}

:where(.input-group-lg > .g-form-input) {
    height: var(--field-height-large);
    padding: var(--field-padding-y-large) var(--field-padding-x-large);
    border-radius: var(--field-radius-large);
}

// Group size classes scale the font from the medium size, so the field matches the group's buttons
.input-group-sm > .g-form-input {
    font-size: calc(var(--font-size-medium) * 0.875);
}

.input-group-lg > .g-form-input {
    font-size: calc(var(--font-size-medium) * 1.25);
}

// Joined fields overlap borders by 1px; page-level margin rules on input elements would beat :where()
.input-group > .g-form-input + .g-form-input,
.input-group > .g-form-input + .form-control,
.input-group > .form-control + .g-form-input {
    margin-left: -1px;
}

// After every rule that sets a radius, since all of them have zero specificity
:where(.input-group > .g-form-input:not(:last-child)) {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

:where(.input-group > .g-form-input:not(:first-child)) {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
}
</style>
