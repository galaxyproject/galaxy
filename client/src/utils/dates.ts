import { format, formatDistanceToNow, parseISO } from "date-fns";

/**
 * Converts a Galaxy time string to a Date object.
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {Date} The parsed Date object.
 */
export function galaxyTimeToDate(galaxyTime: string): Date {
    // Galaxy doesn't include Zulu time zone designator, but it's always UTC
    // so we need to add it to parse the string correctly in JavaScript.
    let time = galaxyTime;
    if (!time.endsWith("Z")) {
        time += "Z";
    }
    const date = parseISO(time);
    if (isNaN(date.getTime())) {
        throw new Error(`Invalid galaxyTime string: ${galaxyTime}`);
    }
    return date;
}

/**
 * Formats a UTC Date object into a human-readable string, localized to the user's time zone.
 * @param {Date} utcDate - The UTC Date object.
 * @returns {string} The formatted date string.
 */
export function localizeUTCPretty(utcDate: Date): string {
    return format(utcDate, "eeee MMM do H:mm:ss yyyy zz");
}

/**
 * Converts a Galaxy time string to a human-readable formatted date string, localized to the user's time zone.
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {string} The formatted date string.
 */
export function formatGalaxyPrettyDateString(galaxyTime: string): string {
    const date = galaxyTimeToDate(galaxyTime);
    return localizeUTCPretty(date);
}

/**
 * Relative label for a Galaxy update time, e.g. "updated 3 days ago".
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {string | undefined} The label, or `undefined` for a missing or malformed time.
 */
export function relativeUpdatedLabel(galaxyTime?: string | null): string | undefined {
    if (!galaxyTime) {
        return undefined;
    }
    try {
        return `updated ${formatDistanceToNow(galaxyTimeToDate(galaxyTime), { addSuffix: true })}`;
    } catch {
        return undefined;
    }
}

/**
 * Short local date label for a Galaxy time string, e.g. "Aug 31, 2026".
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {string | undefined} The label, or `undefined` for a missing or malformed time.
 */
export function shortDateLabel(galaxyTime?: string | null): string | undefined {
    if (!galaxyTime) {
        return undefined;
    }
    try {
        return format(galaxyTimeToDate(galaxyTime), "MMM d, yyyy");
    } catch {
        return undefined;
    }
}
