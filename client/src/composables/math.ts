/**
 * There are similar functions to those in this module in vue-use, but they only work one-way.
 * Unlike vue-use, these composables return refs which can be set.
 */

import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed, type Ref } from "vue";

/**
 * Wraps a number ref, restricting it's values to a given range
 *
 * @param ref ref containing a number to wrap
 * @param min lowest possible value of range
 * @param max highest possible value of range
 * @returns clamped ref
 */
export function useClamp(ref: Ref<number>, min: MaybeRefOrGetter<number>, max: MaybeRefOrGetter<number>): Ref<number> {
    const clamp = (value: number) => {
        return Math.min(Math.max(value, toValue(min)), toValue(max));
    };

    const clampedRef = computed<number>({
        get: () => {
            return clamp(ref.value);
        },
        set: (value) => {
            ref.value = clamp(value);
        },
    });

    return clampedRef;
}

/**
 * Wraps a number ref, restricting it's values to align to a given step size
 *
 * @param ref ref containing a number to wrap
 * @param [stepSize = 1] size of steps to restrict value to. defaults to 1
 * @returns wrapped red
 */
export function useStep(ref: Ref<number>, stepSize: MaybeRefOrGetter<number> = 1): Ref<number> {
    const step = (value: number) => {
        const stepSizeValue = toValue(stepSize);
        return Math.round(value / stepSizeValue) * stepSizeValue;
    };

    const steppedRef = computed<number>({
        get: () => {
            return step(ref.value);
        },
        set: (value) => {
            ref.value = step(value);
        },
    });

    return steppedRef;
}
