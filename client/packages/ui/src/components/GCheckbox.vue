<script setup lang="ts">
/**
 * A checkbox/switch component with optional label.
 * Supports v-model for two-way binding.
 */

import { computed } from "vue";

const props = defineProps<{
    /** The v-model value (checked state) */
    value?: boolean;
    /** ID attribute for the checkbox input */
    id?: string;
    /** Disabled state */
    disabled?: boolean;
    /** Render as a toggle switch instead of a checkbox */
    toggle?: boolean;
}>();

const emit = defineEmits<{
    (e: "input", value: boolean): void;
    (e: "change", event: Event): void;
}>();

const currentValue = computed({
    get() {
        return props.value ?? false;
    },
    set(newValue: boolean) {
        emit("input", newValue);
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
            type="checkbox"
            class="g-checkbox-input"
            :data-test-id="id ? `${id}-input` : undefined"
            :checked="currentValue"
            :disabled="disabled"
            @change="onChange" />
        <span v-if="toggle" class="g-switch-slider" />
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

    .g-switch & {
        // Visually hide the checkbox in switch mode, keeping it accessible
        position: absolute;
        opacity: 0;
        width: 0;
        height: 0;
        pointer-events: none;
    }
}

.g-checkbox-label {
    margin-left: var(--spacing-2, 0.5rem);
}

// Switch/toggle styles
.g-switch {
    position: relative;

    .g-switch-slider {
        position: relative;
        display: inline-block;
        width: 2rem;
        height: 1.125rem;
        background-color: var(--color-grey-400, #adb5bd);
        border-radius: 1rem;
        transition: background-color 0.15s ease-in-out;

        &::before {
            content: "";
            position: absolute;
            top: 0.125rem;
            left: 0.125rem;
            width: 0.875rem;
            height: 0.875rem;
            background-color: white;
            border-radius: 50%;
            transition: transform 0.15s ease-in-out;
        }
    }

    .g-checkbox-input:checked + .g-switch-slider {
        background-color: var(--color-blue-500, #007bff);

        &::before {
            transform: translateX(0.875rem);
        }
    }

    .g-checkbox-input:focus + .g-switch-slider {
        box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
    }

    &.g-disabled .g-switch-slider {
        opacity: 0.5;
    }
}
</style>
