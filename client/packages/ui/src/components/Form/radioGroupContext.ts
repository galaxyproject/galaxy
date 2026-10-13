import type { ComputedRef, InjectionKey } from "vue";

import type { ComponentColor, ComponentSize } from "../componentVariants";

/** One entry of GRadioGroup's `options` prop. */
export interface RadioGroupOption<T = unknown> {
    /** Label shown next to the radio */
    text: string;
    /** Value the group's v-model takes when this radio is selected */
    value: T;
    /** Disables this option only */
    disabled?: boolean;
}

/** Look of a radio in button mode: a GButton color, optionally outlined. */
export type RadioButtonVariant = ComponentColor | `outline-${ComponentColor}`;

/** What a GRadioGroup shares with the GRadio children it renders or wraps. */
export interface RadioGroupContext {
    buttons: ComputedRef<boolean>;
    buttonVariant: ComputedRef<RadioButtonVariant>;
    disabled: ComputedRef<boolean>;
    name: ComputedRef<string>;
    size: ComputedRef<ComponentSize | undefined>;
    isChecked: (value: unknown) => boolean;
    select: (value: unknown) => void;
}

export const radioGroupKey: InjectionKey<RadioGroupContext> = Symbol("g-radio-group");
