<script setup lang="ts">
/**
 * One bar of a GProgress, with role="progressbar" and its value range. Inside a GProgress it takes
 * the progress's `max` and display options unless it sets its own, so several bars stack into one
 * track. Give each bar an `aria-label` (or `aria-labelledby`), since screen readers announce bars
 * one by one. Attributes such as `title`, `data-*` and tooltip directives land on the bar.
 *
 * Content, by priority: the default slot, `label`, the value (`showValue`), the percentage. Bars
 * show their percentage by default because some fills fall below 3:1 against the track; set
 * `:show-progress="false"` only where text has no room or the value is shown nearby; those fills
 * then mark their end. Below 5% of `max` the percentage is dropped the same way, since it would be
 * clipped; `aria-valuenow` still carries the value. A bar with no fill renders no content.
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
    /** Show the percentage; on by default, false hides the percentage */
    showProgress?: boolean;
    /** Show the value instead of the percentage */
    showValue?: boolean;
    /** Decimal places of the shown percentage or value */
    precision?: number | string;
}

// These fills fall below 3:1 against the grey-200 track, so a bar without text marks its fill end
const VARIANTS_BELOW_TRACK_CONTRAST: ProgressVariant[] = ["success", "warning", "info"];
// Narrower fills clip the percentage into unreadable fragments
const MIN_PERCENT_FOR_TEXT = 5;

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
    // A bar's own showProgress outranks the showValue it would inherit
    if (props.showValue ?? (props.showProgress ? false : progress?.showValue.value)) {
        return value.value.toFixed(precision.value);
    }
    if ((props.showProgress ?? progress?.showProgress.value) !== false && percent.value >= MIN_PERCENT_FOR_TEXT) {
        return `${percent.value.toFixed(precision.value)}%`;
    }
    return "";
});

const needsMarker = computed(
    () =>
        VARIANTS_BELOW_TRACK_CONTRAST.includes(variant.value) &&
        percent.value > 0 &&
        percent.value < 100 &&
        !text.value,
);

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
        :class="[classes, { 'g-progress-bar-marked': needsMarker && !$slots.default }]"
        :style="{ width }"
        role="progressbar"
        aria-valuemin="0"
        :aria-valuemax="max"
        :aria-valuenow="valueNow"
        :aria-valuetext="props.label">
        <slot v-if="percent > 0">{{ text }}</slot>
    </div>
</template>

<style scoped lang="scss">
.g-progress-bar {
    // Darkening stripes keep text at 4.5:1 on every fill; dark sets light ones
    --g-progress-stripe: rgb(0% 0% 0% / 0.15);

    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
    overflow: hidden;
    // White text here, grey-900 on the light fills: whichever reaches 4.5:1 on the fill and its stripes
    color: var(--background-color);
    text-align: center;
    white-space: nowrap;
    transition: width 0.6s ease;

    @media (prefers-reduced-motion: reduce) {
        transition: none;
    }

    &.g-primary {
        background-color: var(--color-blue-600);
    }

    &.g-secondary {
        background-color: var(--color-grey-500);
    }

    &.g-success {
        background-color: var(--color-green-500);
        color: var(--color-grey-900);
    }

    &.g-danger {
        background-color: var(--color-red-600);
    }

    &.g-warning {
        background-color: var(--color-orange-600);
        color: var(--color-grey-900);
    }

    &.g-info {
        background-color: var(--color-blue-400);
        color: var(--color-grey-900);
    }

    &.g-dark {
        background-color: var(--color-grey-800);
        --g-progress-stripe: rgb(100% 100% 100% / 0.15);
    }

    &.g-progress-bar-marked {
        box-shadow: inset -2px 0 0 var(--color-grey-800);
    }

    &.g-progress-bar-striped {
        background-image: linear-gradient(
            45deg,
            var(--g-progress-stripe) 25%,
            transparent 25%,
            transparent 50%,
            var(--g-progress-stripe) 50%,
            var(--g-progress-stripe) 75%,
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
