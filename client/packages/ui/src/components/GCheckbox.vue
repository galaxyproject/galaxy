<script setup lang="ts">
/**
 * A checkbox/switch component with optional label.
 * Supports v-model for two-way binding.
 */

import { computed } from "vue";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

const props = defineProps<{
    /** The v-model value (checked state) */
    modelValue?: boolean;
    /** ID attribute for the checkbox input */
    id?: string;
    /** Accessible name when no visible label is provided */
    ariaLabel?: string;
    /** Disabled state */
    disabled?: boolean;
    /** Render as a toggle switch instead of a checkbox */
    toggle?: boolean;
    /** Partly-checked state, e.g. a select-all box when only some rows are selected */
    indeterminate?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
    (e: "change", event: Event): void;
}>();

const currentValue = computed({
    get() {
        return props.modelValue ?? false;
    },
    set(newValue: boolean) {
        emit("update:modelValue", newValue);
    },
});

function onChange(event: Event) {
    const target = event.target as HTMLInputElement;
    currentValue.value = target.checked;
    emit("change", event);
}
</script>

<template>
    <label
        class="g-checkbox"
        :class="{ 'g-disabled': disabled, 'g-switch': toggle }"
        :data-test-id="id ? `${id}-label` : undefined">
        <input
            :id="id"
            :aria-label="ariaLabel"
            type="checkbox"
            class="g-checkbox-input"
            :data-test-id="id ? `${id}-input` : undefined"
            :checked="currentValue"
            :indeterminate="indeterminate"
            :disabled="disabled"
            :role="toggle ? 'switch' : undefined"
            @change="onChange" />
        <span v-if="$slots.default" class="g-checkbox-label">
            <slot></slot>
        </span>
    </label>
</template>

<style scoped lang="scss">
.g-checkbox {
    display: inline-flex;
    align-items: center;
    margin: 0;
    cursor: pointer;
    user-select: none;

    &.g-disabled {
        cursor: not-allowed;
        opacity: 0.6;
    }
}

.g-checkbox-input {
    margin: 0;
    cursor: pointer;

    .g-disabled & {
        cursor: not-allowed;
    }

    &:focus-visible {
        outline: 2px solid var(--color-blue-500, #197cd2);
        outline-offset: 2px;
    }
}

.g-checkbox-label {
    margin-left: var(--spacing-2, 0.5rem);
}

// Switch: the input itself is the track, so it stays visible, clickable and focusable
.g-switch .g-checkbox-input {
    --g-switch-width: 2rem;
    --g-switch-height: 1.125rem;
    --g-switch-knob-color: var(--color-grey-500, #63656d);

    appearance: none;
    box-sizing: border-box;
    flex-shrink: 0;
    width: var(--g-switch-width);
    height: var(--g-switch-height);
    // Off-state border keeps >= 3:1 against the page (WCAG 1.4.11) and survives forced-colors mode
    border: 1px solid var(--color-grey-500, #63656d);
    border-radius: calc(var(--g-switch-height) / 2);
    background-color: var(--background-color, #ffffff);
    background-image: radial-gradient(circle closest-side, var(--g-switch-knob-color) 75%, transparent 80%);
    background-position: left center;
    background-repeat: no-repeat;
    background-size: calc(var(--g-switch-height) - 2px) calc(var(--g-switch-height) - 2px);
    transition:
        background-position 0.15s ease-in-out,
        background-color 0.15s ease-in-out;

    &:checked {
        --g-switch-knob-color: #ffffff;

        border-color: var(--color-blue-500, #197cd2);
        background-color: var(--color-blue-500, #197cd2);
        background-position: right center;
    }

    @media (prefers-reduced-motion: reduce) {
        transition: none;
    }

    // Forced colors drop the knob gradient, which would hide the on/off state; fall back to the native box
    @media (forced-colors: active) {
        appearance: auto;
        width: auto;
        height: auto;
    }
}
</style>
