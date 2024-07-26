import { client } from "@/api/schema";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import { type CleanableItem, CleanableSummary, CleanupResult, PaginationOptions } from "./Cleanup/model";

export async function fetchDiscardedDatasetsSummary(): Promise<CleanableSummary> {
    const { data, error } = await client.GET("/api/storage/datasets/discarded/summary");

    if (error) {
        rethrowSimple(error);
    }

    return new CleanableSummary(data);
}

export async function fetchDiscardedDatasets(options?: PaginationOptions): Promise<CleanableItem[]> {
    options = options ?? new PaginationOptions();
    const { data, error } = await client.GET("/api/storage/datasets/discarded", {
        params: { query: options },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function cleanupDatasets(items: CleanableItem[]): Promise<CleanupResult> {
    const itemIds = items.map((item) => item.id);
    const { data, error } = await client.DELETE("/api/storage/datasets", {
        body: { item_ids: itemIds },
    });

    if (error) {
        return new CleanupResult(undefined, items, errorMessageAsString(error));
    }

    return new CleanupResult(data, items);
}

export async function fetchDiscardedHistoriesSummary(): Promise<CleanableSummary> {
    const { data, error } = await client.GET("/api/storage/histories/discarded/summary");

    if (error) {
        rethrowSimple(error);
    }

    return new CleanableSummary(data);
}

export async function fetchDiscardedHistories(options?: PaginationOptions): Promise<CleanableItem[]> {
    options = options ?? new PaginationOptions();

    const { data, error } = await client.GET("/api/storage/histories/discarded", {
        params: { query: options },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function cleanupHistories(items: CleanableItem[]) {
    const itemIds = items.map((item) => item.id);
    const { data, error } = await client.DELETE("/api/storage/histories", {
        body: { item_ids: itemIds },
    });

    if (error) {
        return new CleanupResult(undefined, items, errorMessageAsString(error));
    }

    return new CleanupResult(data, items);
}

export async function fetchArchivedHistoriesSummary(): Promise<CleanableSummary> {
    const { data, error } = await client.GET("/api/storage/histories/archived/summary");

    if (error) {
        rethrowSimple(error);
    }

    return new CleanableSummary(data);
}

export async function fetchArchivedHistories(options?: PaginationOptions): Promise<CleanableItem[]> {
    options = options ?? new PaginationOptions();
    const { data, error } = await client.GET("/api/storage/histories/archived", {
        params: { query: options },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}
