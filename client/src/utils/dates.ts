import { format, parseISO } from "date-fns";

export function galaxyTimeToDate(galaxyTime: string): Date {
    // We likely don't have tzinfo, but this will always be UTC coming
    // from Galaxy so append Z to assert that prior to parsing
    if (!galaxyTime.endsWith("Z")) {
        galaxyTime += "Z";
    }
    const date = parseISO(galaxyTime);
    return date;
}

export function formatUTCPrettyString(utcDate: Date): string {
    return format(utcDate, "eeee MMM do H:mm:ss yyyy zz");

    return utcDate.toLocaleString("default", {
        day: "numeric",
        month: "long",
        year: "numeric",
        minute: "numeric",
        hour: "numeric",
        timeZone: "UTC",
        timeZoneName: "short",
    });
}

export function formatGalaxyPrettyDateString(galaxyTime: string): string {
    const date = galaxyTimeToDate(galaxyTime);
    return formatUTCPrettyString(date);
}
