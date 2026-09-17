import * as vega from "vega";

import { bytesToString } from "@/utils/utils";

import type { DataValuePoint } from ".";

// Register bytesToString as a Vega expression function so axis labels can use it
(vega as any).expressionFunction("bytesToString", (value: number) => bytesToString(value));

export function bytesLabelFormatter(dataPoint?: DataValuePoint | null): string {
    return dataPoint ? `${dataPoint.label}: ${bytesToString(dataPoint.value)}` : "No data";
}

/** Vega expression for byte-formatted Y-axis labels. */
export const BYTES_AXIS_LABEL_EXPR = "bytesToString(datum.value)";
