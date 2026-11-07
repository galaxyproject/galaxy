const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

function count(value: number, unit: string): string {
    return `${value} ${unit}${value === 1 ? "" : "s"}`;
}

/**
 * Rounded label for a duration in seconds, e.g. "30 minutes", "24 hours" or "7 days".
 * Durations under two days are given in hours, so the one day default reads "24 hours".
 * @param {number} seconds - The duration in seconds.
 * @returns {string | undefined} The label, or `undefined` for a missing, non-numeric or non-positive duration.
 */
export function formatDurationSeconds(seconds?: number | null): string | undefined {
    if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0) {
        return undefined;
    }
    if (seconds < HOUR) {
        return count(Math.max(1, Math.round(seconds / MINUTE)), "minute");
    }
    if (seconds < 2 * DAY) {
        return count(Math.round(seconds / HOUR), "hour");
    }
    return count(Math.round(seconds / DAY), "day");
}
