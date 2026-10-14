<script setup lang="ts" generic="T">
/**
 * A native `<select>` bound with v-model.
 *
 * Renders `options`, then any `<option>` children from the default slot. Option values keep their
 * type (objects, `null`, numbers), and an object model selects the option with an equal value.
 * Attributes (`id`, `name`, `aria-*`, `class`) land on the select: name it with a `<label for>`
 * pointing at its `id`, or with `aria-label` when there is no visible label.
 */

import { computed } from "vue";

import { type ComponentSize, prefix } from "../componentVariants";
import type { SelectOption } from "./GSelect.types";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

interface Props {
    /**
     * Disables the select
     * @default false
     */
    disabled?: boolean;
    /**
     * The v-model value: the value of the chosen option
     * @default undefined
     */
    modelValue?: T;
    /**
     * Options to render before the default slot
     * @default []
     */
    options?: SelectOption<T>[];
    /**
     * Displayed size
     * @default "medium"
     */
    size?: ComponentSize;
    /**
     * Validation state: `false` marks the select invalid, `true` valid, `null` shows neither
     * @default null
     */
    state?: boolean | null;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    modelValue: undefined,
    options: () => [],
    size: "medium",
    state: null,
});

const emit = defineEmits<{
    (e: "update:modelValue", value: T): void;
    (e: "change", event: Event): void;
}>();

// Vue's select v-model reads each option's bound value, so non-string values need no index mapping
const selected = computed({
    get() {
        return props.modelValue;
    },
    set(value) {
        emit("update:modelValue", value as T);
    },
});
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- the caller names it via label for/aria-label -->
    <select
        v-model="selected"
        class="g-select"
        :class="[prefix(size), { 'g-disabled': disabled, 'g-invalid': state === false, 'g-valid': state === true }]"
        :aria-invalid="state === false ? 'true' : undefined"
        :disabled="disabled"
        @change="(event: Event) => emit('change', event)">
        <option v-for="(option, index) in options" :key="index" :disabled="option.disabled" :value="option.value">
            {{ option.text }}
        </option>

        <slot />
    </select>
</template>

<style scoped lang="scss">
.g-select {
    display: inline-block;
    width: 100%;
    height: calc(1.5em + 0.75rem + 2px);
    padding: 0.375rem 1.75rem 0.375rem 0.75rem;
    font-size: var(--font-size-medium, 0.85rem);
    line-height: 1.5;
    color: var(--color-grey-800, #23262f);
    vertical-align: middle;
    // Native arrows differ per browser; draw one caret instead
    appearance: none;
    background: var(--background-color, #ffffff)
        url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='4' height='5' viewBox='0 0 4 5'%3e%3cpath fill='%2323262f' d='M2 0L0 2h4zm0 5L0 3h4z'/%3e%3c/svg%3e")
        right 0.75rem center / 8px 10px no-repeat;
    // grey-500 keeps the border >= 3:1 against the page (WCAG 1.4.11)
    border: 1px solid var(--color-grey-500, #63656d);
    border-radius: var(--spacing-1, 0.25rem);
    cursor: pointer;

    &:focus-visible {
        outline: 2px solid var(--color-blue-500, #197cd2);
        outline-offset: 1px;
    }

    &.g-disabled {
        color: var(--color-grey-600, #484a52);
        background-color: var(--color-grey-100, #f8f9fa);
        cursor: not-allowed;
    }

    &.g-invalid {
        border-color: var(--color-red-600, #e31a1e);
    }

    &.g-valid {
        border-color: var(--color-green-700, #006f50);
    }

    &.g-small {
        height: calc(1.5em + 0.5rem + 2px);
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
        padding-left: 0.5rem;
        font-size: var(--font-size-small, 0.75rem);
    }

    &.g-large {
        height: calc(1.5em + 1rem + 2px);
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 1rem;
        font-size: var(--font-size-large, 1rem);
    }

    // Forced colors drop the background caret; fall back to the native arrow
    @media (forced-colors: active) {
        appearance: auto;
        background-image: none;
    }
}
</style>
