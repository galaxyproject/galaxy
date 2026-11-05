import { until, useDocumentVisibility, useThrottleFn } from "@vueuse/core";
import { defineStore } from "pinia";
import { computed, effectScope, ref, watch } from "vue";

import { type AnyUser, isAdminUser, isAnonymousUser, isRegisteredUser, type RegisteredUser } from "@/api";
import { getGalaxyInstance } from "@/app";
import { useHashedUserId } from "@/composables/hashedUserId";
import { useKeyedCache } from "@/composables/keyedCache";
import { useSSE } from "@/composables/useNotificationSSE";
import { useUserLocalStorageFromHashId } from "@/composables/userLocalStorageFromHashedId";
import { useConfigStore } from "@/stores/configurationStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import {
    addFavoriteEdamOperationQuery,
    addFavoriteEdamTopicQuery,
    addFavoriteTagQuery,
    addFavoriteToolQuery,
    decodeIdById,
    type FavoriteOrderEntry,
    type FavoriteSummary,
    getCurrentUser,
    removeFavoriteEdamOperationQuery,
    removeFavoriteEdamTopicQuery,
    removeFavoriteTagQuery,
    removeFavoriteToolQuery,
    setCurrentThemeQuery,
    updateFavoriteOrderQuery,
} from "@/stores/users/queries";

interface FavoriteObjects {
    tools: string[];
    tags?: string[];
    edam_operations?: string[];
    edam_topics?: string[];
    order?: FavoriteOrderEntry[];
}

interface Preferences {
    theme?: string;
    favorites: FavoriteObjects;
    [key: string]: unknown;
}

export type ListViewMode = "grid" | "list";

type UserListViewPreferences = Record<string, ListViewMode>;

const RECENT_TOOLS_LIMIT = 10;

/** Minimum time between storage usage refreshes triggered by frequent changes. */
const STORAGE_REFRESH_THROTTLE_MS = 5000;
/** Minimum time between storage usage refreshes when the user returns to the tab. */
const FOCUS_REFRESH_THROTTLE_MS = 60_000;
/** Upper bound of the random delay before refreshing after an event sent to every user. */
const BROADCAST_REFRESH_MAX_DELAY_MS = 30_000;
/** Upper bound of the random delay before catching up after live updates reconnect, e.g. when Galaxy restarts. */
const RECONNECT_REFRESH_MAX_DELAY_MS = 10_000;
/** How long to wait for live updates to reconnect when the user returns to the tab, before refreshing anyway. */
const WAKE_RECONNECT_TIMEOUT_MS = 10_000;

function isBroadcastEvent(event: MessageEvent): boolean {
    try {
        return JSON.parse(event.data)?.broadcast === true;
    } catch {
        return false;
    }
}

export const useUserStore = defineStore("userStore", () => {
    const currentUser = ref<AnyUser>(null);
    const currentPreferences = ref<Preferences | null>(null);
    const { hashedUserId } = useHashedUserId(currentUser);

    const currentListViewPreferences = useUserLocalStorageFromHashId<UserListViewPreferences>(
        "user-store-list-view-preferences",
        {},
        hashedUserId,
    );

    const hasSeenUploadHelp = useUserLocalStorageFromHashId("user-store-seen-upload-help", false, hashedUserId);

    const historyPanelWidth = useUserLocalStorageFromHashId("user-store-history-panel-width", 300, hashedUserId);

    const chatPanelWidth = useUserLocalStorageFromHashId("user-store-chat-panel-width", 400, hashedUserId);

    const recentTools = useUserLocalStorageFromHashId<string[]>("user-store-recent-tools", [], hashedUserId);

    let loadPromise: Promise<void> | null = null;
    let lastLoadRequest = 0;
    let lastAppliedRequest = 0;

    function $reset() {
        currentUser.value = null;
        currentPreferences.value = null;
        recentTools.value = [];
        loadPromise = null;
        decodedIdCache.value = {};
    }

    const isAdmin = computed(() => {
        return isAdminUser(currentUser.value);
    });

    const isAnonymous = computed(() => {
        return isAnonymousUser(currentUser.value);
    });

    const currentTheme = computed(() => {
        return currentPreferences.value?.theme ?? null;
    });

    const currentFavorites = computed(() => {
        return normalizeFavorites(currentPreferences.value?.favorites);
    });

    const matchesCurrentUsername = computed(() => {
        return (username?: string) => {
            return isRegisteredUser(currentUser.value) && currentUser.value.username === username;
        };
    });

    const matchesCurrentUserId = computed(() => {
        return (userId?: string) => {
            return isRegisteredUser(currentUser.value) && "id" in currentUser.value && currentUser.value.id === userId;
        };
    });

    function setCurrentUser(user: RegisteredUser) {
        currentUser.value = user;
    }

    function setUserState(user: AnyUser) {
        if (isRegisteredUser(user)) {
            currentUser.value = user;
            const preferences = processUserPreferences(user);
            // Refreshes return the same preferences most of the time: don't wake their watchers for nothing
            if (JSON.stringify(preferences) !== JSON.stringify(currentPreferences.value)) {
                currentPreferences.value = preferences;
            }
        } else if (isAnonymousUser(user)) {
            currentUser.value = user;
        } else if (user === null) {
            currentUser.value = null;
        }
    }

    function refreshUser(includeHistories = false) {
        loadPromise = null;
        return loadUser(includeHistories);
    }

    /**
     * Reloads the user, which reports the usage and quota of the default storage, and the usage of
     * every storage source if anything asked for it.
     */
    async function refreshStorageUsage() {
        const quotaUsageStore = useQuotaUsageStore();
        await Promise.all([refreshUser(), quotaUsageStore.wasRequested ? quotaUsageStore.loadQuotaUsages(true) : null]);
    }

    /** Like ``refreshStorageUsage``, without waiting for it; errors are logged. */
    function refreshStorageUsageInBackground() {
        refreshStorageUsage().catch((err) => console.error("Error refreshing the storage usage:", err));
    }

    const throttledRefresh = useThrottleFn(refreshStorageUsageInBackground, STORAGE_REFRESH_THROTTLE_MS, true, true);
    const refreshOnFocus = useThrottleFn(refreshStorageUsageInBackground, FOCUS_REFRESH_THROTTLE_MS, false, true);

    let delayedRefreshPending = false;

    function refreshAfterDelay() {
        delayedRefreshPending = false;
        refreshStorageUsageThrottled();
    }

    /**
     * Refreshes after a random delay, for changes that reach many browsers at once, so that their
     * refetches are spread out. A refresh already scheduled runs after this change too.
     */
    function refreshAfterRandomDelay(maxDelayMs: number) {
        if (!delayedRefreshPending) {
            delayedRefreshPending = true;
            setTimeout(refreshAfterDelay, Math.random() * maxDelayMs);
        }
    }

    function onQuotaEvent(event: MessageEvent) {
        if (isBroadcastEvent(event)) {
            // A default quota changed for every user
            refreshAfterRandomDelay(BROADCAST_REFRESH_MAX_DELAY_MS);
        } else {
            refreshStorageUsageThrottled();
        }
    }

    const { connect: connectQuotaEvents, connected: sseConnected } = useSSE(onQuotaEvent, ["user_quota_update"]);
    const documentVisibility = useDocumentVisibility();
    let watchingStorageUsage = false;
    let liveUpdatesEnabled = false;
    let refreshSkippedWhileHidden = false;
    let catchUpOnWakeReconnect = false;

    /**
     * Catches up without live updates if they haven't reconnected since the user returned, e.g. when
     * a proxy blocks them.
     */
    function catchUpIfNotReconnected() {
        if (catchUpOnWakeReconnect) {
            catchUpOnWakeReconnect = false;
            refreshStorageUsageThrottled();
        }
    }

    /**
     * Like ``refreshStorageUsageInBackground``, at most once per window: a workflow finishing many
     * jobs changes the usage, and sends an event, for each. While the tab is hidden, it refreshes
     * once the user returns.
     */
    function refreshStorageUsageThrottled() {
        if (watchingStorageUsage && documentVisibility.value === "hidden") {
            refreshSkippedWhileHidden = true;
            return;
        }
        void throttledRefresh();
    }

    /**
     * Call it after anything that changes the storage usage, e.g. a purge or a history growing.
     * While live updates are connected, the server announces the change itself, so it does nothing.
     * Anonymous users get no usage events, so their usage is still refreshed.
     */
    function refreshStorageUsageUnlessLive() {
        if (!(liveUpdatesEnabled && sseConnected.value && isRegisteredUser(currentUser.value))) {
            refreshStorageUsageThrottled();
        }
    }

    // Watchers created after an ``await`` belong to no scope; this one ends with the store
    const storageUsageScope = effectScope();

    /**
     * Keeps the storage usage current: refresh when the user returns to the tab and, with live
     * updates, on the server's ``user_quota_update`` events.
     */
    async function startWatchingStorageUsage() {
        if (watchingStorageUsage) {
            return;
        }
        watchingStorageUsage = true;
        storageUsageScope.run(() => {
            // Quota events don't cover changes made outside Galaxy's code, e.g. by cleanup scripts
            watch(documentVisibility, (visibility) => {
                if (visibility !== "visible") {
                    return;
                }
                if (liveUpdatesEnabled && !sseConnected.value) {
                    // Live updates reconnect when the user returns, and catch up then
                    catchUpOnWakeReconnect = true;
                    refreshSkippedWhileHidden = false;
                    setTimeout(catchUpIfNotReconnected, WAKE_RECONNECT_TIMEOUT_MS);
                } else if (refreshSkippedWhileHidden) {
                    // A change is known to be missing: don't wait for the next focus refresh
                    refreshSkippedWhileHidden = false;
                    void throttledRefresh();
                } else {
                    void refreshOnFocus();
                }
            });
        });
        const configStore = useConfigStore();
        await until(() => configStore.isLoaded).toBe(true);
        storageUsageScope.run(() => {
            if (configStore.config?.enable_sse_updates) {
                liveUpdatesEnabled = true;
                connectQuotaEvents();
                let connectedBefore = sseConnected.value;
                watch(sseConnected, (isConnected) => {
                    // Events sent while disconnected are lost; the first connection has nothing to catch up on
                    if (isConnected && catchUpOnWakeReconnect) {
                        catchUpOnWakeReconnect = false;
                        refreshStorageUsageThrottled();
                    } else if (isConnected && connectedBefore) {
                        // Every open tab reconnects at once when Galaxy restarts
                        refreshAfterRandomDelay(RECONNECT_REFRESH_MAX_DELAY_MS);
                    }
                    connectedBefore ||= isConnected;
                });
            }
        });
    }

    function loadUser(includeHistories = true) {
        if (!loadPromise) {
            const request = ++lastLoadRequest;
            const promise = (async () => {
                const user = await getCurrentUser();
                // Overlapping requests can answer out of order. Apply any answer newer than the last one
                // applied, even while a later request is pending, so that code awaiting this one sees a user.
                if (request > lastAppliedRequest) {
                    lastAppliedRequest = request;
                    setUserState(user);
                }
                if (includeHistories) {
                    await useHistoryStore().loadHistories();
                }
            })().catch((e) => {
                // A failed load must be retryable without resetting the user state.
                // An older request must not clear a newer refresh's cached promise.
                if (loadPromise === promise) {
                    loadPromise = null;
                }
                throw e;
            });
            loadPromise = promise;
        }
        return loadPromise; // Return the shared promise
    }

    async function setCurrentTheme(theme: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const currentTheme = await setCurrentThemeQuery(currentUser.value.id, theme);
        if (currentPreferences.value) {
            currentPreferences.value.theme = currentTheme;
        }
    }
    async function addFavoriteTool(toolId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await addFavoriteToolQuery(currentUser.value.id, toolId);
        setFavorites(favorites);
    }

    async function removeFavoriteTool(toolId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await removeFavoriteToolQuery(currentUser.value.id, toolId);
        setFavorites(favorites);
    }

    async function addFavoriteTag(tag: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await addFavoriteTagQuery(currentUser.value.id, tag);
        setFavorites(favorites);
    }

    async function removeFavoriteTag(tag: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await removeFavoriteTagQuery(currentUser.value.id, tag);
        setFavorites(favorites);
    }

    async function addFavoriteEdamOperation(operationId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await addFavoriteEdamOperationQuery(currentUser.value.id, operationId);
        setFavorites(favorites);
    }

    async function removeFavoriteEdamOperation(operationId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await removeFavoriteEdamOperationQuery(currentUser.value.id, operationId);
        setFavorites(favorites);
    }

    async function addFavoriteEdamTopic(topicId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await addFavoriteEdamTopicQuery(currentUser.value.id, topicId);
        setFavorites(favorites);
    }

    async function removeFavoriteEdamTopic(topicId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await removeFavoriteEdamTopicQuery(currentUser.value.id, topicId);
        setFavorites(favorites);
    }

    async function reorderFavorites(order: FavoriteOrderEntry[]) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const favorites = await updateFavoriteOrderQuery(currentUser.value.id, order);
        setFavorites(favorites);
    }

    function setFavorites(favorites: Partial<FavoriteSummary>) {
        if (currentPreferences.value) {
            currentPreferences.value.favorites = normalizeFavorites(favorites);
        }
    }

    function addRecentTool(toolId: string) {
        if (!toolId) {
            return;
        }
        const currentTools = recentTools.value || [];
        recentTools.value = [toolId, ...currentTools.filter((id) => id !== toolId)].slice(0, RECENT_TOOLS_LIMIT);
    }

    function clearRecentTools() {
        recentTools.value = [];
    }

    function setListViewPreference(listId: string, view: ListViewMode) {
        currentListViewPreferences.value = {
            ...currentListViewPreferences.value,
            [listId]: view,
        };
    }

    function processUserPreferences(user: RegisteredUser): Preferences {
        // Favorites are returned as a JSON string by the API
        const favorites =
            typeof user.preferences.favorites === "string"
                ? normalizeFavorites(JSON.parse(user.preferences.favorites))
                : normalizeFavorites(user.preferences.favorites as Partial<FavoriteSummary> | undefined);
        return {
            ...user.preferences,
            favorites,
        };
    }

    function normalizeFavorites(favorites?: Partial<FavoriteSummary> | null): FavoriteSummary {
        const normalized = {
            tools: favorites?.tools ?? [],
            tags: favorites?.tags ?? [],
            edam_operations: favorites?.edam_operations ?? [],
            edam_topics: favorites?.edam_topics ?? [],
            order: [] as FavoriteOrderEntry[],
        };
        const validObjectIdsByType = {
            tools: new Set(normalized.tools),
            tags: new Set(normalized.tags),
            edam_operations: new Set(normalized.edam_operations),
            edam_topics: new Set(normalized.edam_topics),
        };
        const seen = new Set<string>();
        const order = favorites?.order ?? [];

        for (const entry of order) {
            const objectType = entry?.object_type;
            const objectId = entry?.object_id;
            const entryKey = `${objectType}:${objectId}`;
            if (
                objectType &&
                objectId &&
                objectType in validObjectIdsByType &&
                validObjectIdsByType[objectType as keyof typeof validObjectIdsByType].has(objectId) &&
                !seen.has(entryKey)
            ) {
                seen.add(entryKey);
                normalized.order.push({ object_type: objectType, object_id: objectId });
            }
        }

        const appendMissing = (object_type: FavoriteOrderEntry["object_type"], object_ids: string[]) => {
            for (const object_id of object_ids) {
                const entryKey = `${object_type}:${object_id}`;
                if (!seen.has(entryKey)) {
                    seen.add(entryKey);
                    normalized.order.push({ object_type, object_id });
                }
            }
        };

        appendMissing("tools", normalized.tools);
        appendMissing("tags", normalized.tags);
        appendMissing("edam_operations", normalized.edam_operations);
        appendMissing("edam_topics", normalized.edam_topics);

        return normalized;
    }

    /** Whether the user may decode ids (is an admin), or `null` while that is still unknown.
     * Embedded views (e.g. scratchbook iframes) deliberately leave `currentUser` unloaded, so fall
     * back to the user the legacy Galaxy instance bootstrapped from `/context`. */
    function canDecodeIds(): boolean | null {
        if (currentUser.value !== null) {
            return isAdmin.value;
        }
        const legacyUser = getGalaxyInstance()?.user;
        return legacyUser ? Boolean(legacyUser.isAdmin()) : null;
    }

    async function fetchdecodedIdById(params: { id: string }) {
        if (canDecodeIds()) {
            return await decodeIdById(params.id);
        }
        return null;
    }

    const { getItemById: getDecodedId, storedItems: decodedIdCache } = useKeyedCache<number | null>(
        fetchdecodedIdById,
        // Only fetch a decoded id if the user is known and the item is undefined (not yet cached).
        () => (item?: number | null) => canDecodeIds() !== null && item === undefined,
    );

    return {
        currentUser,
        currentPreferences,
        isAdmin,
        isAnonymous,
        currentTheme,
        currentFavorites,
        currentListViewPreferences,
        getDecodedId,
        hasSeenUploadHelp,
        historyPanelWidth,
        chatPanelWidth,
        recentTools,
        loadUser,
        refreshUser,
        refreshStorageUsage,
        refreshStorageUsageUnlessLive,
        startWatchingStorageUsage,
        matchesCurrentUsername,
        matchesCurrentUserId,
        setCurrentUser,
        setCurrentTheme,
        setListViewPreference,
        addFavoriteTool,
        addFavoriteTag,
        addFavoriteEdamOperation,
        addFavoriteEdamTopic,
        removeFavoriteTool,
        removeFavoriteTag,
        removeFavoriteEdamOperation,
        removeFavoriteEdamTopic,
        reorderFavorites,
        addRecentTool,
        clearRecentTools,
        $reset,
    };
});
