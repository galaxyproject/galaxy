import type { FetchDataResponse } from "@/api/tools";

import type { UploadedDataset } from "./uploadItemTypes";

/**
 * Raw dataset data structure from API response.
 */
interface UploadResponseData {
    id: string;
    name?: string;
    label?: string;
    hid?: number;
    src?: string;
}

function isUploadResponseData(value: unknown): value is UploadResponseData {
    if (!value || typeof value !== "object") {
        return false;
    }
    return "id" in value && typeof value.id === "string";
}

function toUploadedDataset(output: unknown): UploadedDataset | null {
    if (!isUploadResponseData(output) || !output.id) {
        return null;
    }

    return {
        id: output.id,
        name: output.name ?? output.label ?? output.id,
        hid: output.hid,
        src: output.src === "hdca" ? "hdca" : "hda",
    };
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function collectUploadedDatasets(responseOutputs: unknown, datasets: UploadedDataset[]): void {
    if (!responseOutputs) {
        return;
    }

    if (Array.isArray(responseOutputs)) {
        responseOutputs.forEach((item) => collectUploadedDatasets(item, datasets));
        return;
    }

    const converted = toUploadedDataset(responseOutputs);
    if (converted) {
        datasets.push(converted);
        return;
    }

    if (isPlainObject(responseOutputs)) {
        Object.values(responseOutputs).forEach((nested) => collectUploadedDatasets(nested, datasets));
    }
}

/**
 * Extracts uploaded datasets from a fetch response, recursively searching through outputs.
 * @param response - The fetch response containing outputs
 * @returns Array of unique uploaded datasets
 */
export function datasetsFromFetchResponse(response: FetchDataResponse): UploadedDataset[] {
    if (!response.outputs) {
        return [];
    }

    const datasets: UploadedDataset[] = [];
    collectUploadedDatasets(response.outputs, datasets);

    const seen = new Set<string>();
    return datasets.filter((dataset) => {
        if (seen.has(dataset.id)) {
            return false;
        }
        seen.add(dataset.id);
        return true;
    });
}

/**
 * Extracts dataset IDs from a fetch response.
 * @param response - The fetch response containing outputs
 * @returns Array of dataset IDs
 */
export function datasetIdsFromFetchResponse(response: FetchDataResponse): string[] {
    return datasetsFromFetchResponse(response).map((dataset) => dataset.id);
}
