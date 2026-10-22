<script setup lang="ts">
/**
 * Progress track. With `value` and no content it shows one bar and gives it `ariaLabel` /
 * `ariaLabelledby`; with GProgressBar children the bars stack in one track against its `max`, and
 * the track becomes a labelled group. Bars take `max`, `variant`, `striped`, `animated`,
 * `showProgress`, `showValue` and `precision` from here unless they set their own.
 *
 * Attributes such as `class` land on the track.
 */

import { computed, provide, useSlots } from "vue";

import { progressKey, type ProgressVariant, toNumber } from "./progressContext";

import GProgressBar from "./GProgressBar.vue";

interface Props {
    /** Value of the single bar, when there are no GProgressBar children */
    value?: number | string;
    /** Maximum value of the bars */
    max?: number | string;
    /** Bar colour */
    variant?: ProgressVariant;
    /** Visible text of the single bar, also announced as aria-valuetext */
    label?: string;
    /** Diagonal stripes */
    striped?: boolean;
    /** Moving stripes (implies striped); still under prefers-reduced-motion */
    animated?: boolean;
    /** Show the percentage on the bars */
    showProgress?: boolean;
    /** Show the value on the bars */
    showValue?: boolean;
    /** Decimal places of the shown percentage or value */
    precision?: number | string;
    /** Track height, as a CSS length */
    height?: string;
    /** Accessible name: of the single bar, or of the group of stacked bars */
    ariaLabel?: string;
    /** ID of the element naming the single bar or the group */
    ariaLabelledby?: string;
}

const props = withDefaults(defineProps<Props>(), {
    value: 0,
    max: 100,
    variant: undefined,
    label: undefined,
    precision: 0,
    height: undefined,
    ariaLabel: undefined,
    ariaLabelledby: undefined,
});

const slots = useSlots();

const max = computed(() => {
    const max = toNumber(props.max, 100);
    return max > 0 ? max : 100;
});

provide(progressKey, {
    max,
    variant: computed(() => props.variant),
    striped: computed(() => props.striped),
    animated: computed(() => props.animated),
    showProgress: computed(() => props.showProgress),
    showValue: computed(() => props.showValue),
    precision: computed(() => Math.max(Math.floor(toNumber(props.precision, 0)), 0)),
});

const stacked = computed(() => Boolean(slots.default));
</script>

<template>
    <div
        class="g-progress"
        :style="{ height: props.height }"
        :role="stacked && (props.ariaLabel || props.ariaLabelledby) ? 'group' : undefined"
        :aria-label="stacked ? props.ariaLabel : undefined"
        :aria-labelledby="stacked ? props.ariaLabelledby : undefined">
        <slot>
            <GProgressBar
                :value="props.value"
                :label="props.label"
                :aria-label="props.ariaLabel"
                :aria-labelledby="props.ariaLabelledby" />
        </slot>
    </div>
</template>

<style scoped lang="scss">
.g-progress {
    display: flex;
    box-sizing: border-box;
    height: 1rem;
    overflow: hidden;
    border-radius: var(--spacing-1);
    background-color: var(--color-grey-200);
    font-size: var(--font-size-small);
    line-height: 0;
}
</style>
