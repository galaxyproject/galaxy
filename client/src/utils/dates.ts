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

export function localizeUTCPretty(utcDate: Date): string {
    return format(utcDate, "eeee MMM do H:mm:ss yyyy zz");
}

export function formatGalaxyPrettyDateString(galaxyTime: string): string {
    const date = galaxyTimeToDate(galaxyTime);
    return localizeUTCPretty(date);
}
