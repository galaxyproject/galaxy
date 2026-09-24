import type { FetchDataResponse } from "@/api/tools";

import type { UploadedDataset } from "./uploadItemTypes";

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

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function collectResponseEntries(responseField: unknown, entries: UploadResponseData[]): void {
    if (!responseField) {
        return;
    }

    if (Array.isArray(responseField)) {
        responseField.forEach((item) => collectResponseEntries(item, entries));
        return;
    }

    if (isUploadResponseData(responseField) && responseField.id) {
        entries.push(responseField);
        return;
    }

    if (isPlainObject(responseField)) {
        Object.values(responseField).forEach((nested) => collectResponseEntries(nested, entries));
    }
}

function deduplicateById(datasets: UploadedDataset[]): UploadedDataset[] {
    const seen = new Set<string>();
    return datasets.filter((dataset) => {
        if (seen.has(dataset.id)) {
            return false;
        }
        seen.add(dataset.id);
        return true;
    });
}

function entryName(entry: UploadResponseData): string {
    return entry.name ?? entry.label ?? entry.id;
}

export function datasetsFromFetchResponse(response: FetchDataResponse): UploadedDataset[] {
    const entries: UploadResponseData[] = [];
    collectResponseEntries(response.outputs, entries);

    return deduplicateById(
        entries.map((entry) => ({
            id: entry.id,
            name: entryName(entry),
            hid: entry.hid,
            src: entry.src === "hdca" ? "hdca" : "hda",
        })),
    );
}

export function datasetCollectionsFromFetchResponse(response: FetchDataResponse): UploadedDataset[] {
    const entries: UploadResponseData[] = [];
    collectResponseEntries(response.output_collections, entries);

    return deduplicateById(
        entries.map((entry) => ({
            id: entry.id,
            name: entryName(entry),
            hid: entry.hid,
            src: "hdca" as const,
        })),
    );
}

export function datasetIdsFromFetchResponse(response: FetchDataResponse): string[] {
    return datasetsFromFetchResponse(response).map((dataset) => dataset.id);
}
