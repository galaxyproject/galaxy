import { format, parseISO } from "date-fns";

/**
 * Converts a Galaxy time string to a Date object.
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {Date} The parsed Date object.
 */
export function galaxyTimeToDate(galaxyTime: string): Date {
    // We likely don't have tzinfo, but this will always be UTC coming
    // from Galaxy so append Z to assert that prior to parsing
    if (!galaxyTime.endsWith("Z")) {
        galaxyTime += "Z";
    }
    const date = parseISO(galaxyTime);
    return date;
}

/**
 * Formats a UTC Date object into a human-readable string.
 * @param {Date} utcDate - The UTC Date object.
 * @returns {string} The formatted date string.
 */
export function localizeUTCPretty(utcDate: Date): string {
    return format(utcDate, "eeee MMM do H:mm:ss yyyy zz");
}

/**
 * Converts a Galaxy time string to a human-readable formatted date string.
 * @param {string} galaxyTime - The Galaxy time string in ISO format.
 * @returns {string} The formatted date string.
 */
export function formatGalaxyPrettyDateString(galaxyTime: string): string {
    const date = galaxyTimeToDate(galaxyTime);
    return localizeUTCPretty(date);
}
