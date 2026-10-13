/** One entry of GSelect's `options` prop. */
export interface SelectOption<T = unknown> {
    /** Label shown for the option */
    text: string;
    /** Value bound to the select's v-model when the option is chosen */
    value: T;
    /** Disables this option only */
    disabled?: boolean;
}
