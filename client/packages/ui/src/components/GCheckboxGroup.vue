<script setup lang="ts">
/**
 * A group of checkboxes bound to one array with v-model.
 *
 * Renders `options`, then any GCheckbox children from the default slot. Checking appends the
 * value in click order, unchecking removes it. The root is a `<fieldset>`: give it a `label`
 * (or a `label` slot) for a visible legend, or pass `aria-label` / `aria-labelledby` when the
 * label lives outside the group.
 */

import { computed, provide } from "vue";

import { useUid } from "../composables/uid";
import { checkboxGroupKey, type CheckboxGroupOption, looseEqual } from "./checkboxGroupContext";
import type { ComponentSize } from "./componentVariants";

import GCheckbox from "./GCheckbox.vue";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

interface Props {
    /**
     * Disables every checkbox in the group
     * @default false
     */
    disabled?: boolean;
    /**
     * Visible legend for the group
     * @default undefined
     */
    label?: string;
    /**
     * The v-model value: values of the checked boxes, in the order they were checked
     * @default []
     */
    modelValue?: unknown[];
    /**
     * Name shared by every checkbox input
     * @default an auto-generated unique name
     */
    name?: string;
    /**
     * Checkboxes to render before the default slot
     * @default []
     */
    options?: CheckboxGroupOption[];
    /**
     * Size of every checkbox in the group
     * @default undefined (surrounding font size)
     */
    size?: ComponentSize;
    /**
     * Stack the checkboxes vertically instead of in a wrapping row
     * @default false
     */
    stacked?: boolean;
    /**
     * Render every checkbox as a toggle switch
     * @default false
     */
    switches?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    label: undefined,
    modelValue: () => [],
    name: undefined,
    options: () => [],
    size: undefined,
    stacked: false,
    switches: false,
});

const emit = defineEmits<{
    (e: "update:modelValue", value: unknown[]): void;
}>();

const uid = useUid("g-checkbox-group-");

const groupName = computed(() => props.name ?? uid.value);

function isChecked(value: unknown) {
    return props.modelValue.some((selected) => looseEqual(selected, value));
}

function toggle(value: unknown, checked: boolean) {
    const others = props.modelValue.filter((selected) => !looseEqual(selected, value));
    emit("update:modelValue", checked ? [...others, value] : others);
}

provide(checkboxGroupKey, {
    disabled: computed(() => props.disabled),
    name: groupName,
    size: computed(() => props.size),
    switches: computed(() => props.switches),
    isChecked,
    toggle,
});
</script>

<template>
    <fieldset class="g-checkbox-group" :disabled="disabled">
        <legend v-if="label || $slots.label" class="g-checkbox-group-legend">
            <slot name="label">{{ label }}</slot>
        </legend>

        <div class="g-checkbox-group-options" :class="{ 'g-stacked': stacked }">
            <GCheckbox
                v-for="(option, index) in options"
                :key="index"
                :disabled="option.disabled"
                :value="option.value">
                {{ option.text }}
            </GCheckbox>

            <slot />
        </div>
    </fieldset>
</template>

<style scoped lang="scss">
.g-checkbox-group {
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
}

.g-checkbox-group-legend {
    width: auto;
    margin-bottom: var(--spacing-1, 0.25rem);
    padding: 0;
    font-size: inherit;
}

.g-checkbox-group-options {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-1, 0.25rem) var(--spacing-4, 1rem);

    &.g-stacked {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
