import type { CleanableItem } from "./model";

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
