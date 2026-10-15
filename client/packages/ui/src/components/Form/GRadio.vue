<script setup lang="ts">
/**
 * A native radio button with optional label. Supports v-model: the radio is checked when its
 * `value` loosely equals the v-model, and selecting it emits that `value`. Give radios that
 * belong together the same `name`, so the browser handles arrow keys and the single tab stop.
 *
 * `class`, `style`, `title` and native listeners land on the root label; every other attribute
 * (`data-test-id`, `aria-*`) lands on the input, so give an unlabeled radio an `aria-label`.
 *
 * Inside a GRadioGroup the group owns the state: the radio emits `change` but not
 * `update:modelValue`, takes the group's name and size unless it sets its own, always follows the
 * group's disabled, and renders as a button when the group sets `buttons`.
 */

import { computed, inject, useAttrs } from "vue";

import { looseEqual } from "../../utils/looseEqual";
import { type ComponentSize, prefix } from "../componentVariants";
import { radioGroupKey } from "./radioGroupContext";

defineOptions({
    inheritAttrs: false,
    // Under @vue/compat: keep v-model on modelValue, and keep class/style/listeners in $attrs so they can be split below
    compatConfig: { COMPONENT_V_MODEL: false, INSTANCE_ATTRS_CLASS_STYLE: false, INSTANCE_LISTENERS: false },
});

const props = defineProps<{
    /** The v-model value: the value of the selected radio */
    modelValue?: unknown;
    /** ID attribute for the radio input */
    id?: string;
    /** Accessible name when no visible label is provided */
    ariaLabel?: string;
    /** Disabled state */
    disabled?: boolean;
    /** Name attribute for the radio input; radios sharing it form one keyboard group */
    name?: string;
    /** Required attribute for the radio input */
    required?: boolean;
    /** Displayed size; unset keeps the surrounding font size */
    size?: ComponentSize;
    /** Value this radio stands for, also rendered as the input's value attribute */
    value?: unknown;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: unknown): void;
    (e: "change", event: Event): void;
}>();

const attrs = useAttrs();

const group = inject(radioGroupKey, null);

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

const isChecked = computed(() => (group ? group.isChecked(props.value) : looseEqual(props.modelValue, props.value)));

const isDisabled = computed(() => props.disabled || Boolean(group?.disabled.value));

const inputName = computed(() => props.name ?? group?.name.value);

const buttonClasses = computed(() => {
    if (!group?.buttons.value) {
        return undefined;
    }
    const variant = group.buttonVariant.value;
    const outline = variant.startsWith("outline-");
    return ["g-radio-button", prefix(outline ? variant.slice("outline-".length) : variant), { "g-outline": outline }];
});

const sizeClass = computed(() => {
    const size = props.size ?? group?.size.value;
    return size ? prefix(size) : undefined;
});

// title stays on the label so v-g-tooltip, which binds to the root, can read and suppress it
function isRootAttr(key: string) {
    return key === "class" || key === "style" || key === "title" || /^on[A-Z]/.test(key);
}

// A radio only fires change when it becomes checked, so this is always a selection
function onChange(event: Event) {
    if (group) {
        group.select(props.value);
    } else {
        emit("update:modelValue", props.value);
    }
    emit("change", event);
}
</script>

<template>
    <label
        v-bind="rootAttrs()"
        class="g-radio"
        :class="[sizeClass, buttonClasses, { 'g-checked': isChecked, 'g-disabled': isDisabled }]">
        <input
            v-bind="inputAttrs()"
            :id="id"
            :aria-label="ariaLabel"
            type="radio"
            class="g-radio-input"
            :checked="isChecked"
            :disabled="isDisabled"
            :name="inputName"
            :required="required"
            :value="value"
            @change="onChange" />
        <span v-if="$slots.default" class="g-radio-label">
            <slot></slot>
        </span>
    </label>
</template>

<style scoped lang="scss">
.g-radio {
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

.g-radio-input {
    margin: 0 3px 0 0;
    accent-color: var(--color-blue-600, #25537b);
    cursor: pointer;

    .g-disabled & {
        cursor: not-allowed;
    }

    &:focus-visible {
        outline: 2px solid var(--color-blue-500, #197cd2);
        outline-offset: 2px;
    }
}

.g-radio-label {
    margin-left: var(--spacing-2, 0.5rem);
}

.g-small {
    font-size: var(--font-size-small, 0.75rem);

    .g-radio-input {
        width: 0.75rem;
        height: 0.75rem;
    }
}

.g-large {
    font-size: var(--font-size-large, 1rem);

    .g-radio-input {
        width: 1.25rem;
        height: 1.25rem;
    }
}

// Button mode: GButton's look on the label; the input stays in the DOM, visually hidden, so keyboard and AT still use it
.g-radio-button {
    position: relative;
    padding: var(--spacing-1, 0.25rem) var(--spacing-2, 0.5rem);
    border: 1px solid;
    border-radius: var(--spacing-1, 0.25rem);
    font-size: var(--font-size-medium, 0.875rem);

    &.g-small {
        font-size: var(--font-size-small, 0.75rem);
    }

    &.g-large {
        padding: var(--spacing-2, 0.5rem) var(--spacing-3, 0.75rem);
        font-size: var(--font-size-large, 1rem);
    }

    .g-radio-input {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip-path: inset(50%);
        white-space: nowrap;
    }

    .g-radio-label {
        margin-left: 0;
    }

    &:has(.g-radio-input:focus-visible) {
        z-index: 1;
        box-shadow: 0 0 0 0.2rem var(--color-blue-400);
        // forced-colors mode drops box-shadow; the transparent outline then renders in the system color
        outline: 2px solid transparent;
        outline-offset: 2px;
    }

    &.g-grey {
        background-color: var(--color-grey-200);
        border-color: var(--color-grey-300);
        color: var(--color-grey-800);

        &:hover {
            background-color: var(--color-grey-300);
        }

        &.g-checked {
            background-color: var(--color-grey-400);
            border-color: var(--color-grey-600);
        }

        &.g-outline {
            background-color: var(--background-color);
            border-color: var(--color-grey-600);
            color: var(--color-grey-600);

            &:hover:not(.g-checked) {
                background-color: var(--color-grey-200);
            }

            &.g-checked {
                background-color: var(--color-grey-600);
                color: var(--color-grey-100);
            }
        }
    }

    @each $color in "blue", "green", "red", "yellow", "orange" {
        &.g-#{$color} {
            background-color: var(--color-#{$color}-600);
            border-color: var(--color-#{$color}-600);
            color: var(--color-#{$color}-100);

            &:hover {
                background-color: var(--color-#{$color}-700);
            }

            &.g-checked {
                background-color: var(--color-#{$color}-800);
                border-color: var(--color-#{$color}-900);
            }

            &.g-outline {
                background-color: var(--background-color);
                color: var(--color-#{$color}-600);

                &:hover:not(.g-checked) {
                    background-color: var(--color-#{$color}-200);
                }

                &.g-checked {
                    background-color: var(--color-#{$color}-600);
                    color: var(--color-#{$color}-100);
                }
            }
        }
    }

    // Forced colors drop the backgrounds that mark the selected button; keep it visible with a system-colored outline
    @media (forced-colors: active) {
        &.g-checked {
            outline: 2px solid Highlight;
            outline-offset: -3px;
        }
    }
}
</style>
