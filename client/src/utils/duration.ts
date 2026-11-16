const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

function count(value: number, unit: string): string {
    return `${value} ${unit}${value === 1 ? "" : "s"}`;
}

/**
 * Label for a duration in seconds, rounded up, e.g. "30 minutes", "24 hours" or "7 days".
 * Durations under two days are given in hours, so the one day default reads "24 hours".
 * @param {number} seconds - The duration in seconds.
 * @returns {string | undefined} The label, or `undefined` for a missing, non-numeric or non-positive duration.
 */
export function formatDurationSeconds(seconds?: number | null): string | undefined {
    if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0) {
        return undefined;
    }
    const minutes = Math.ceil(seconds / MINUTE);
    if (minutes < HOUR / MINUTE) {
        return count(minutes, "minute");
    }
    const hours = Math.ceil(seconds / HOUR);
    if (hours < (2 * DAY) / HOUR) {
        return count(hours, "hour");
    }
    return count(Math.ceil(seconds / DAY), "day");
}
