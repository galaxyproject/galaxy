import type Filtering from "@/utils/filtering";

/** A quick-pick time range; its duration is used to compute a `<filter>_gt` cutoff from "now". */
export interface TimeRange {
    key: string;
    label: string;
    durationMs: number;
}

/** The active range for a manually-entered range filter, which no quick-pick range matches. */
export const CUSTOM_TIME_RANGE = "custom";

/** The `<filter>_gt` value a quick-pick range was applied as, and the range key it came from,
 * so a caller can later tell that range apart from a manually-entered `<filter>` filter
 * ("custom") by comparing this value against the filter text's current `<filter>_gt`. */
export interface AppliedTimeRange {
    key: string;
    value: string;
}

/**
 * Sets or clears a `TimeRangeFilter` quick-pick, overloading the existing `<filterName>_gt`
 * filter instead of introducing a new one.
 * @returns The updated filter text, and the applied range (`undefined` when clearing), for the
 *          caller to track and later pass back into its own "custom" detection.
 */
export function setActiveTimeRange<T>(
    filtering: Filtering<T>,
    filterName: string,
    filterText: string,
    range: TimeRange | undefined,
): { filterText: string; appliedRange: AppliedTimeRange | undefined } {
    const after = `${filterName}_gt`;
    if (!range) {
        return {
            filterText: filtering.applyFiltersToText({ [after]: "" } as Record<string, T>, filterText, true),
            appliedRange: undefined,
        };
    }
    const cutoff = currentTimeRangeCutoff(range);
    const newText = filtering.applyFiltersToText({ [after]: cutoff } as Record<string, T>, filterText);
    return {
        filterText: newText,
        appliedRange: { key: range.key, value: String(filtering.getFilterValue(newText, after)) },
    };
}

/**
 * Recomputes a quick-pick range's `<filter>_gt` cutoff as of right now, rather than the fixed
 * value `setActiveTimeRange` wrote into the filter text at pick time. Used to keep a periodic
 * re-check's own query live without rewriting the filter text itself (which would also disturb
 * `getActiveTimeRange`'s stored `lastApplied` comparison and anything else keyed on filter text).
 */
export function currentTimeRangeCutoff(range: TimeRange): string {
    return new Date(Date.now() - range.durationMs).toISOString();
}

/**
 * Derives the active `TimeRangeFilter` quick-pick from filter text: "custom" for a
 * manually-entered `<filterName>` filter, or `undefined` for "Anytime".
 * @param lastApplied The range `setActiveTimeRange` itself last applied (its own return value),
 *                     to tell it apart from a manually-entered `<filterName>` filter.
 */
export function getActiveTimeRange<T>(
    filtering: Filtering<T>,
    filterName: string,
    filterText: string,
    lastApplied: AppliedTimeRange | undefined,
): string | undefined {
    const after = filtering.getFilterValue(filterText, `${filterName}_gt`);
    const before = filtering.getFilterValue(filterText, `${filterName}_lt`);
    if (!after && !before) {
        return undefined;
    }
    if (!before && lastApplied !== undefined && lastApplied.value === String(after)) {
        return lastApplied.key;
    }
    return CUSTOM_TIME_RANGE;
}
