import { bytesToString } from "@/utils/utils";

import { type DataValuePoint } from ".";

export function bytesLabelFormatter(dataPoint?: DataValuePoint | null): string {
    return dataPoint ? `${dataPoint.label}: ${bytesToString(dataPoint.value)}` : "No data";
}

export function bytesValueFormatter(value: number): string {
    return bytesToString(value);
}
