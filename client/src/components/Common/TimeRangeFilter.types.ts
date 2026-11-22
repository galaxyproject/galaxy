/** A quick-pick time range: a duration back from now. */
export interface TimeRange {
    key: string;
    label: string;
    durationMs: number;
}

/** The active range for a manually-entered range filter, which no quick-pick range matches. */
export const CUSTOM_TIME_RANGE = "custom";
