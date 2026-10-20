<script setup lang="ts" generic="T">
/**
 * A group of radios bound to one value with v-model.
 *
 * Renders `options`, then any GRadio children from the default slot, all under one shared `name`
 * so the browser gives the group a single tab stop and arrow-key navigation. The root is a
 * `<fieldset role="radiogroup">`: give it a `label` (or a `label` slot) for a visible legend, or
 * pass `aria-label` / `aria-labelledby` when the label lives outside the group.
 */

import { computed, provide } from "vue";

import { useUid } from "../../composables/uid";
import { looseEqual } from "../../utils/looseEqual";
import type { ComponentSize } from "../componentVariants";
import { type RadioButtonVariant, radioGroupKey, type RadioGroupOption } from "./radioGroupContext";

import GRadio from "./GRadio.vue";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

interface Props {
    /**
     * Render the radios as a row of joined buttons
     * @default false
     */
    buttons?: boolean;
    /**
     * Button color in button mode, optionally prefixed with `outline-`
     * @default "grey"
     */
    buttonVariant?: RadioButtonVariant;
    /**
     * Disables every radio in the group
     * @default false
     */
    disabled?: boolean;
    /**
     * Visible legend for the group
     * @default undefined
     */
    label?: string;
    /**
     * Extra classes for the legend, e.g. to tighten its spacing
     * @default undefined
     */
    legendClass?: string | string[] | Record<string, boolean>;
    /**
     * The v-model value: the value of the selected radio
     * @default undefined
     */
    modelValue?: T;
    /**
     * Name shared by every radio input
     * @default an auto-generated unique name
     */
    name?: string;
    /**
     * Radios to render before the default slot
     * @default []
     */
    options?: RadioGroupOption<T>[];
    /**
     * Size of every radio in the group
     * @default undefined (surrounding font size)
     */
    size?: ComponentSize;
    /**
     * Stack the radios vertically instead of in a wrapping row
     * @default false
     */
    stacked?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    buttons: false,
    buttonVariant: "grey",
    disabled: false,
    label: undefined,
    legendClass: undefined,
    modelValue: undefined,
    name: undefined,
    options: () => [],
    size: undefined,
    stacked: false,
});

const emit = defineEmits<{
    (e: "update:modelValue", value: T): void;
}>();

const uid = useUid("g-radio-group-");

const groupName = computed(() => props.name ?? uid.value);

const legendId = computed(() => `${uid.value}-legend`);

function isChecked(value: unknown) {
    return looseEqual(props.modelValue, value);
}

// GRadio children are untyped, so their value is trusted to be a T
function select(value: unknown) {
    emit("update:modelValue", value as T);
}

provide(radioGroupKey, {
    buttons: computed(() => props.buttons),
    buttonVariant: computed(() => props.buttonVariant),
    disabled: computed(() => props.disabled),
    name: groupName,
    size: computed(() => props.size),
    isChecked,
    select,
});
</script>

<template>
    <!-- A fieldset with a role is not reliably named by its legend, so point at the legend explicitly -->
    <fieldset
        class="g-radio-group"
        role="radiogroup"
        :aria-labelledby="label || $slots.label ? legendId : undefined"
        :disabled="disabled">
        <legend v-if="label || $slots.label" :id="legendId" class="g-radio-group-legend" :class="legendClass">
            <slot name="label">{{ label }}</slot>
        </legend>

        <div class="g-radio-group-options" :class="{ 'g-buttons': buttons, 'g-stacked': stacked }">
            <GRadio v-for="(option, index) in options" :key="index" :disabled="option.disabled" :value="option.value">
                {{ option.text }}
            </GRadio>

            <slot />
        </div>
    </fieldset>
</template>

<style scoped lang="scss">
.g-radio-group {
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
}

.g-radio-group-legend {
    width: auto;
    margin-bottom: 0;
    // Form labels' padding plus the 1px field border, not a spacing step, so a labelled group lines up with labelled fields
    padding: 0 0 calc(0.375rem + 1px);
    font-size: inherit;
}

.g-radio-group-options {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--spacing-4, 1rem);

    &.g-stacked {
        flex-direction: column;
        align-items: flex-start;
    }

    // Joined like GButtonGroup: square inner corners, no doubled borders
    &.g-buttons {
        display: inline-flex;
        flex-wrap: nowrap;
        gap: 0;
        vertical-align: middle;

        &:not(.g-stacked) {
            > :deep(.g-radio-button:not(:first-child)) {
                margin-left: -1px;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }

            > :deep(.g-radio-button:not(:last-child)) {
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }
        }

        &.g-stacked {
            align-items: stretch;

            > :deep(.g-radio-button:not(:first-child)) {
                margin-top: -1px;
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }

            > :deep(.g-radio-button:not(:last-child)) {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }
        }
    }
}
</style>
