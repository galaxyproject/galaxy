import type { ComputedRef, InjectionKey } from "vue";

import type { ComponentSize } from "./componentVariants";

/** One entry of GCheckboxGroup's `options` prop. */
export interface CheckboxGroupOption {
    /** Label shown next to the checkbox */
    text: string;
    /** Value added to the group's v-model when checked */
    value: unknown;
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

/**
 * Group membership test, loose like BFormCheckboxGroup: objects match by JSON form, other values by
 * string form, so a numeric option still matches a value that came back from the server as a string.
 */
export function looseEqual(a: unknown, b: unknown): boolean {
    if (a === b) {
        return true;
    }
    if (typeof a === "object" && a !== null && typeof b === "object" && b !== null) {
        return JSON.stringify(a) === JSON.stringify(b);
    }
    if (typeof a === "object" || typeof b === "object") {
        return false;
    }
    return String(a) === String(b);
}
