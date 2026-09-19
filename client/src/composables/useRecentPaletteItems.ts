import { computed, type Ref } from "vue";

import { useHashedUserId } from "@/composables/hashedUserId";
import { useUserLocalStorageFromHashId } from "@/composables/userLocalStorageFromHashedId";
import { useUserStore } from "@/stores/userStore";

/** Maximum number of remembered entries, per entity type */
export const RECENT_PALETTE_ITEMS_LIMIT = 10;

const STORAGE_KEY = "command-palette-recent-items";

/** One item the user opened through the command palette */
export interface RecentPaletteItem {
    /** Entity type, e.g. "history", "workflow", "dataset" */
    type: string;
    /** Entity id, unique within its type */
    id: string;
    /** Display name at the time the item was opened */
    name: string;
    /** Router location the item navigates to, when it has one */
    to?: string;
}

type RecentPaletteItemsByType = Record<string, RecentPaletteItem[]>;

let storedItems: Ref<RecentPaletteItemsByType> | null = null;

function isRecentPaletteItem(value: unknown): value is RecentPaletteItem {
    const item = value as RecentPaletteItem | null;
    return (
        !!item &&
        typeof item === "object" &&
        typeof item.type === "string" &&
        typeof item.id === "string" &&
        typeof item.name === "string" &&
        (item.to === undefined || typeof item.to === "string")
    );
}

/** Local storage may hold anything; keep only well formed entries. */
function sanitize(entries: unknown): RecentPaletteItem[] {
    if (!Array.isArray(entries)) {
        return [];
    }
    return entries.filter(isRecentPaletteItem);
}

function useStoredItems(): Ref<RecentPaletteItemsByType> {
    if (!storedItems) {
        const userStore = useUserStore();
        const { hashedUserId } = useHashedUserId(computed(() => userStore.currentUser));
        storedItems = useUserLocalStorageFromHashId<RecentPaletteItemsByType>(
            STORAGE_KEY,
            {},
            hashedUserId,
        ) as Ref<RecentPaletteItemsByType>;
    }
    return storedItems;
}

/**
 * Most recently used items opened through the command palette, persisted per
 * user (same mechanism as `userStore.recentTools`). Entries are kept per entity
 * type, in MRU order, deduplicated by type and id and capped at
 * `RECENT_PALETTE_ITEMS_LIMIT`.
 */
export function useRecentPaletteItems() {
    const items = useStoredItems();

    /** Remembered items of `type`, most recently used first */
    function recentItems(type: string): RecentPaletteItem[] {
        if (!type) {
            return [];
        }
        return sanitize(items.value[type]);
    }

    /** Record `entry` as the most recently used item of its type */
    function addRecentItem(entry: RecentPaletteItem) {
        if (!entry?.type || !entry?.id) {
            return;
        }
        const item: RecentPaletteItem = {
            type: entry.type,
            id: entry.id,
            name: entry.name ?? "",
            ...(entry.to === undefined ? {} : { to: entry.to }),
        };
        const remaining = recentItems(entry.type).filter((existing) => existing.id !== item.id);
        items.value = {
            ...items.value,
            [item.type]: [item, ...remaining].slice(0, RECENT_PALETTE_ITEMS_LIMIT),
        };
    }

    /** Forget the items of `type`, or all remembered items when omitted */
    function clearRecentItems(type?: string) {
        if (type === undefined) {
            items.value = {};
            return;
        }
        if (!(type in items.value)) {
            return;
        }
        const remaining = { ...items.value };
        delete remaining[type];
        items.value = remaining;
    }

    return { recentItems, addRecentItem, clearRecentItems };
}
