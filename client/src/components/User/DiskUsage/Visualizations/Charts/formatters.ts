import type { DataValuePoint } from ".";

import { bytesToString } from "@/utils/utils";

export function bytesLabelFormatter(dataPoint?: DataValuePoint | null): string {
    return dataPoint ? `${dataPoint.label}: ${bytesToString(dataPoint.value)}` : "No data";
}

export function bytesValueFormatter(value: number): string {
    return bytesToString(value);
}
