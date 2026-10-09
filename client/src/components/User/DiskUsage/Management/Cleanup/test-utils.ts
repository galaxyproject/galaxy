import { type CleanableItem, CleanableSummary, type CleanupOperation, CleanupResult } from "./model";

export function getFakeCleanableItem(overrides: Partial<CleanableItem> = {}): CleanableItem {
    return {
        id: "item-id",
        name: "Test item",
        size: 512,
        type: "dataset",
        update_time: "2024-01-01T00:00:00.000Z",
        ...overrides,
    };
}

export function getFakeCleanupOperation(overrides: Partial<CleanupOperation> = {}): CleanupOperation {
    return {
        id: "operation-id",
        name: "operation name",
        description: "operation description",
        fetchSummary: async () => new CleanableSummary({ total_size: 0, total_items: 0 }),
        fetchItems: async () => [],
        cleanupItems: async () => new CleanupResult(),
        ...overrides,
    };
}
