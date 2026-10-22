<script setup lang="ts">
/**
 * One bar of a GProgress, with role="progressbar" and its value range. Inside a GProgress it takes
 * the progress's `max` and display options unless it sets its own, so several bars stack into one
 * track. Give each bar an `aria-label` (or `aria-labelledby`), since screen readers announce bars
 * one by one. Attributes such as `title`, `data-*` and tooltip directives land on the bar.
 *
 * Content, by priority: the default slot, `label`, the percentage (`showProgress`), the value
 * (`showValue`).
 */

import { computed, inject } from "vue";

import { prefix } from "./componentVariants";
import { progressKey, type ProgressVariant, toNumber } from "./progressContext";

interface Props {
    /** Current value, from 0 to `max` */
    value?: number | string;
    /** Maximum value; defaults to the enclosing GProgress's, else 100 */
    max?: number | string;
    /** Bar colour; defaults to the enclosing GProgress's, else primary */
    variant?: ProgressVariant;
    /** Visible text, also announced as aria-valuetext */
    label?: string;
    /** Diagonal stripes */
    striped?: boolean;
    /** Moving stripes (implies striped); still under prefers-reduced-motion */
    animated?: boolean;
    /** Show the percentage */
    showProgress?: boolean;
    /** Show the value */
    showValue?: boolean;
    /** Decimal places of the shown percentage or value */
    precision?: number | string;
}

const props = withDefaults(defineProps<Props>(), {
    value: 0,
    max: undefined,
    variant: undefined,
    label: undefined,
    striped: undefined,
    animated: undefined,
    showProgress: undefined,
    showValue: undefined,
    precision: undefined,
});

const progress = inject(progressKey, null);

const value = computed(() => toNumber(props.value, 0));
const max = computed(() => {
    const own = toNumber(props.max, 0);
    const max = own > 0 ? own : (progress?.max.value ?? 100);
    return max > 0 ? max : 100;
});
const precision = computed(() => Math.max(Math.floor(toNumber(props.precision, progress?.precision.value ?? 0)), 0));
const percent = computed(() => (100 * value.value) / max.value);
const width = computed(() => `${Math.min(Math.max(percent.value, 0), 100)}%`);
// aria-valuenow must lie within aria-valuemin and aria-valuemax
const valueNow = computed(() => Math.min(Math.max(value.value, 0), max.value).toFixed(precision.value));

const variant = computed(() => props.variant ?? progress?.variant.value ?? "primary");
const animated = computed(() => props.animated ?? progress?.animated.value ?? false);
const striped = computed(() => animated.value || (props.striped ?? progress?.striped.value ?? false));

const text = computed(() => {
    if (props.label !== undefined) {
        return props.label;
    }
    if (props.showProgress ?? progress?.showProgress.value) {
        return percent.value.toFixed(precision.value);
    }
    if (props.showValue ?? progress?.showValue.value) {
        return value.value.toFixed(precision.value);
    }
    return "";
});

const classes = computed(() => ({
    [prefix(variant.value)]: true,
    "g-progress-bar-striped": striped.value,
    "g-progress-bar-animated": animated.value,
    "g-progress-bar-empty": percent.value <= 0,
}));
</script>

<template>
    <div
        class="g-progress-bar"
        :class="classes"
        :style="{ width }"
        role="progressbar"
        aria-valuemin="0"
        :aria-valuemax="max"
        :aria-valuenow="valueNow"
        :aria-valuetext="props.label">
        <slot>{{ text }}</slot>
    </div>
</template>

<style scoped lang="scss">
.g-progress-bar {
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
    overflow: hidden;
    // Page-colour text keeps 4.5:1 on every fill; info, the one light fill, sets dark text
    color: var(--background-color);
    text-align: center;
    white-space: nowrap;
    transition: width 0.6s ease;

    @media (prefers-reduced-motion: reduce) {
        transition: none;
    }

    // Each fill keeps 3:1 against the grey-200 track, and its text 4.5:1 against the fill
    &.g-primary {
        background-color: var(--color-blue-600);
    }

    &.g-secondary {
        background-color: var(--color-grey-500);
    }

    &.g-success {
        background-color: var(--color-green-700);
    }

    &.g-danger {
        background-color: var(--color-red-600);
    }

    &.g-warning {
        background-color: var(--color-yellow-700);
    }

    &.g-info {
        background-color: var(--color-blue-500);
        color: var(--color-blue-900);
    }

    &.g-dark {
        background-color: var(--color-grey-800);
    }

    &.g-progress-bar-striped {
        background-image: linear-gradient(
            45deg,
            rgb(100% 100% 100% / 0.15) 25%,
            transparent 25%,
            transparent 50%,
            rgb(100% 100% 100% / 0.15) 50%,
            rgb(100% 100% 100% / 0.15) 75%,
            transparent 75%,
            transparent
        );
        background-size: 1rem 1rem;
    }

    &.g-progress-bar-animated {
        animation: g-progress-stripes 1s linear infinite;

        @media (prefers-reduced-motion: reduce) {
            animation: none;
        }
    }
}

// A page-coloured seam between stacked fills, so neighbours need no contrast with each other
.g-progress-bar:not(.g-progress-bar-empty) ~ .g-progress-bar:not(.g-progress-bar-empty) {
    border-left: 1px solid var(--background-color);
}

@keyframes g-progress-stripes {
    from {
        background-position: 1rem 0;
    }

    to {
        background-position: 0 0;
    }
}
</style>
