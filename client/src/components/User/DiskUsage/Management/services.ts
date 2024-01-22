import { fetcher } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

import { type CleanableItem, CleanableSummary, CleanupResult, PaginationOptions } from "./Cleanup/model";

const discardedDatasetsSummaryFetcher = fetcher.path("/api/storage/datasets/discarded/summary").method("get").create();

export async function fetchDiscardedDatasetsSummary(): Promise<CleanableSummary> {
    try {
        const { data } = await discardedDatasetsSummaryFetcher({});
        return new CleanableSummary(data);
    } catch (e) {
        rethrowSimple(e);
    }
}

const discardedDatasetsFetcher = fetcher.path("/api/storage/datasets/discarded").method("get").create();

export async function fetchDiscardedDatasets(options?: PaginationOptions): Promise<CleanableItem[]> {
    try {
        options = options ?? new PaginationOptions();
        const { data } = await discardedDatasetsFetcher({
            offset: options.offset,
            limit: options.limit,
            order: options.order,
        });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

const datasetsCleaner = fetcher.path("/api/storage/datasets").method("delete").create();

export async function cleanupDatasets(items: CleanableItem[]): Promise<CleanupResult> {
    try {
        const item_ids = items.map((item) => item.id);
        const { data } = await datasetsCleaner({
            item_ids,
        });
        return new CleanupResult(data, items);
    } catch (error) {
        return new CleanupResult(undefined, items, error as string);
    }
}

const discardedHistoriesSummaryFetcher = fetcher
    .path("/api/storage/histories/discarded/summary")
    .method("get")
    .create();

export async function fetchDiscardedHistoriesSummary(): Promise<CleanableSummary> {
    try {
        const { data } = await discardedHistoriesSummaryFetcher({});
        return new CleanableSummary(data);
    } catch (e) {
        rethrowSimple(e);
    }
}

const discardedHistoriesFetcher = fetcher.path("/api/storage/histories/discarded").method("get").create();

export async function fetchDiscardedHistories(options?: PaginationOptions): Promise<CleanableItem[]> {
    try {
        options = options ?? new PaginationOptions();
        const { data } = await discardedHistoriesFetcher({
            offset: options.offset,
            limit: options.limit,
            order: options.order,
        });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

const historiesCleaner = fetcher.path("/api/storage/histories").method("delete").create();
export async function cleanupHistories(items: CleanableItem[]) {
    try {
        const item_ids = items.map((item) => item.id);
        const { data } = await historiesCleaner({
            item_ids,
        });
        return new CleanupResult(data, items);
    } catch (error) {
        return new CleanupResult(undefined, items, error as string);
    }
}

const archivedHistoriesSummaryFetcher = fetcher.path("/api/storage/histories/archived/summary").method("get").create();

export async function fetchArchivedHistoriesSummary(): Promise<CleanableSummary> {
    const { data } = await archivedHistoriesSummaryFetcher({});
    return new CleanableSummary(data);
}

const archivedHistoriesFetcher = fetcher.path("/api/storage/histories/archived").method("get").create();

export async function fetchArchivedHistories(options?: PaginationOptions): Promise<CleanableItem[]> {
    options = options ?? new PaginationOptions();
    const { data } = await archivedHistoriesFetcher({
        offset: options.offset,
        limit: options.limit,
        order: options.order,
    });
    return data;
}
