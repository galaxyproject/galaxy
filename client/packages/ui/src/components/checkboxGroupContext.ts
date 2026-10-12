import type { ComputedRef, InjectionKey } from "vue";

import type { ComponentSize } from "./componentVariants";

/** One entry of GCheckboxGroup's `options` prop. */
export interface CheckboxGroupOption<T = unknown> {
    /** Label shown next to the checkbox */
    text: string;
    /** Value added to the group's v-model when checked */
    value: T;
    /** Disables this option only */
    disabled?: boolean;
}

/** What a GCheckboxGroup shares with the GCheckbox children it renders or wraps. */
export interface CheckboxGroupContext {
    disabled: ComputedRef<boolean>;
    name: ComputedRef<string>;
    size: ComputedRef<ComponentSize | undefined>;
    switches: ComputedRef<boolean>;
    isChecked: (value: unknown) => boolean;
    toggle: (value: unknown, checked: boolean) => void;
}

export const checkboxGroupKey: InjectionKey<CheckboxGroupContext> = Symbol("g-checkbox-group");
