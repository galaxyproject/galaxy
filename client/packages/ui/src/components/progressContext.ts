import type { ComputedRef, InjectionKey } from "vue";

import type { ColorVariant } from "./componentVariants";

/** Bar colours. No `light`: a light bar cannot keep 3:1 contrast against the light track. */
export type ProgressVariant = Exclude<ColorVariant, "light">;

/** What a GProgress shares with its GProgressBar children; each bar's own props win. */
export interface ProgressContext {
    max: ComputedRef<number>;
    variant: ComputedRef<ProgressVariant | undefined>;
    striped: ComputedRef<boolean>;
    animated: ComputedRef<boolean>;
    showProgress: ComputedRef<boolean>;
    showValue: ComputedRef<boolean>;
    precision: ComputedRef<number>;
}

export const progressKey: InjectionKey<ProgressContext> = Symbol("g-progress");

export function toNumber(value: number | string | undefined, fallback: number): number {
    const number = typeof value === "string" ? parseFloat(value) : value;
    return number === undefined || Number.isNaN(number) ? fallback : number;
}
