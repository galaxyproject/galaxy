import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type AnyUser, isAdminUser, isAnonymousUser, isRegisteredUser, type RegisteredUser } from "@/api";
import { useHashedUserId } from "@/composables/hashedUserId";
import { useUserLocalStorageFromHashId } from "@/composables/userLocalStorageFromHashedId";
import { useHistoryStore } from "@/stores/historyStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import {
    addFavoriteEdamOperationQuery,
    addFavoriteEdamTopicQuery,
    addFavoriteTagQuery,
    addFavoriteToolQuery,
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

interface LegacyGalaxyAppUserLike {
    attributes: Record<string, unknown>;
}

interface LegacyGalaxyAppLike {
    user?: LegacyGalaxyAppUserLike;
}

const RECENT_TOOLS_LIMIT = 10;

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

    function requestQuotaRefreshForLoadedQuotaStore() {
        const quotaUsageStore = useQuotaUsageStore();
        if (quotaUsageStore.isLoaded) {
            quotaUsageStore.requestRefreshDebounced();
        }
    }

    function shouldRefreshQuotaAfterUserUpdate(previousUser: AnyUser, nextUser: RegisteredUser) {
        if (!isRegisteredUser(previousUser)) {
            return true;
        }

        return (
            previousUser.total_disk_usage !== nextUser.total_disk_usage ||
            previousUser.quota_percent !== nextUser.quota_percent ||
            previousUser.quota !== nextUser.quota
        );
    }

    function $reset() {
        currentUser.value = null;
        currentPreferences.value = null;
        recentTools.value = [];
        loadPromise = null;
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
        const previousUser = currentUser.value;

        if (isRegisteredUser(user)) {
            currentUser.value = user;
            currentPreferences.value = processUserPreferences(user);
            if (shouldRefreshQuotaAfterUserUpdate(previousUser, user)) {
                requestQuotaRefreshForLoadedQuotaStore();
            }
        } else if (isAnonymousUser(user)) {
            currentUser.value = user;
        } else if (user === null) {
            currentUser.value = null;
        }
    }

    /**
     * @deprecated
     * This function bridges the Pinia user store with the legacy
     * jQuery-based Galaxy app's `app.user.attributes` object. Once the legacy
     * app and all its consumers are fully migrated to Vue/Pinia, this sync
     * will no longer be needed and should be removed along with the
     * `LegacyGalaxyAppLike` interface.
     */
    function syncLegacyAppUser(app?: LegacyGalaxyAppLike | null) {
        if (!app?.user || !currentUser.value) {
            return;
        }

        app.user.attributes = {
            ...app.user.attributes,
            ...currentUser.value,
        };
    }

    function refreshUser(includeHistories = false) {
        loadPromise = null;
        return loadUser(includeHistories);
    }

    function loadUser(includeHistories = true) {
        if (!loadPromise) {
            loadPromise = new Promise<void>((resolve, reject) => {
                (async () => {
                    try {
                        const user = await getCurrentUser();
                        setUserState(user);
                        if (includeHistories) {
                            const historyStore = useHistoryStore();
                            await historyStore.loadHistories();
                        }
                        resolve(); // Resolve the promise after successful load
                    } catch (e) {
                        console.error("Failed to load user", e);
                        reject(e); // Reject the promise on error
                    } finally {
                        //Don't clear the loadPromise, we still want multiple callers to await.
                        //Instead we must clear it upon $reset
                        // loadPromise = null;
                    }
                })();
            });
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

    return {
        currentUser,
        currentPreferences,
        isAdmin,
        isAnonymous,
        currentTheme,
        currentFavorites,
        currentListViewPreferences,
        hasSeenUploadHelp,
        historyPanelWidth,
        chatPanelWidth,
        recentTools,
        loadUser,
        refreshUser,
        syncLegacyAppUser,
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
