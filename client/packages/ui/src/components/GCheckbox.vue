<script setup lang="ts">
/**
 * A checkbox/switch component with optional label.
 * Supports v-model for two-way binding.
 *
 * `class`, `style`, `title` and native listeners (`@click.stop`, ...) land on the root label, so
 * non-bubbling `@focus`/`@blur` never fire there (use `@focusin`/`@focusout`). Every other
 * attribute (`data-test-id`, `aria-*`) lands on the input, so give an unlabeled
 * checkbox an `aria-label`.
 *
 * Inside a GCheckboxGroup the group owns the state: the checkbox is checked when its `value` is in
 * the group's v-model, emits `change` but not `update:modelValue`, and takes the group's name, size,
 * disabled and switch mode unless it sets its own.
 */

import { computed, inject, useAttrs } from "vue";

import { checkboxGroupKey } from "./checkboxGroupContext";
import { type ComponentSize, prefix } from "./componentVariants";

defineOptions({
    inheritAttrs: false,
    // Under @vue/compat: keep v-model on modelValue, and keep class/style/listeners in $attrs so they can be split below
    compatConfig: { COMPONENT_V_MODEL: false, INSTANCE_ATTRS_CLASS_STYLE: false, INSTANCE_LISTENERS: false },
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
    /** Partly-checked state, e.g. a select-all box when only some rows are selected */
    indeterminate?: boolean;
    /** Name attribute for the checkbox input */
    name?: string;
    /** Required attribute for the checkbox input */
    required?: boolean;
    /** Displayed size; unset keeps the surrounding font size */
    size?: ComponentSize;
    /** Render as a toggle switch instead of a checkbox */
    toggle?: boolean;
    /** Value attribute for the checkbox input, rendered as a string whenever it is set */
    value?: unknown;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
    (e: "change", event: Event): void;
}>();

const attrs = useAttrs();

const group = inject(checkboxGroupKey, null);

// Plain functions, not computeds: $attrs is not reactive, so the render function must read it each time
function rootAttrs() {
    return {
        "data-test-id": props.id ? `${props.id}-label` : undefined,
        ...Object.fromEntries(Object.entries(attrs).filter(([key]) => isRootAttr(key))),
    };
}

// Caller attributes win over the defaults derived from props
function inputAttrs() {
    return {
        "data-test-id": props.id ? `${props.id}-input` : undefined,
        ...Object.fromEntries(Object.entries(attrs).filter(([key]) => !isRootAttr(key))),
    };
}

const isChecked = computed(() => (group ? group.isChecked(props.value) : (props.modelValue ?? false)));

const isDisabled = computed(() => props.disabled || Boolean(group?.disabled.value));

const isSwitch = computed(() => props.toggle || Boolean(group?.switches.value));

const inputName = computed(() => props.name ?? group?.name.value);

const sizeClass = computed(() => {
    const size = props.size ?? group?.size.value;
    return size ? prefix(size) : undefined;
});

// title stays on the label so v-g-tooltip, which binds to the root, can read and suppress it
function isRootAttr(key: string) {
    return key === "class" || key === "style" || key === "title" || /^on[A-Z]/.test(key);
}

function onChange(event: Event) {
    const target = event.target as HTMLInputElement;
    if (group) {
        group.toggle(props.value, target.checked);
    } else {
        emit("update:modelValue", target.checked);
    }
    emit("change", event);
}
</script>

<template>
    <label
        v-bind="rootAttrs()"
        class="g-checkbox"
        :class="[sizeClass, { 'g-disabled': isDisabled, 'g-switch': isSwitch }]">
        <input
            v-bind="inputAttrs()"
            :id="id"
            :aria-label="ariaLabel"
            type="checkbox"
            class="g-checkbox-input"
            :checked="isChecked"
            :indeterminate="indeterminate"
            :disabled="isDisabled"
            :name="inputName"
            :required="required"
            :role="isSwitch ? 'switch' : undefined"
            :value="value"
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

.g-small {
    font-size: var(--font-size-small, 0.75rem);

    &:not(.g-switch) .g-checkbox-input {
        width: 0.75rem;
        height: 0.75rem;
    }
}

.g-large {
    font-size: var(--font-size-large, 1rem);

    &:not(.g-switch) .g-checkbox-input {
        width: 1.25rem;
        height: 1.25rem;
    }
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

.g-switch.g-small .g-checkbox-input {
    --g-switch-width: 1.5rem;
    --g-switch-height: 0.875rem;
}

.g-switch.g-large .g-checkbox-input {
    --g-switch-width: 2.5rem;
    --g-switch-height: 1.375rem;
}
</style>
