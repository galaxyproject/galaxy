import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type AnyUser, isAdminUser, isAnonymousUser, isRegisteredUser, type RegisteredUser } from "@/api";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useHistoryStore } from "@/stores/historyStore";
import {
    addFavoriteToolQuery,
    getCurrentUser,
    removeFavoriteToolQuery,
    setCurrentThemeQuery,
} from "@/stores/users/queries";

interface FavoriteTools {
    tools: string[];
}

interface Preferences {
    theme?: string;
    favorites: FavoriteTools;
    [key: string]: unknown;
}

export type ListViewMode = "grid" | "list";

type UserListViewPreferences = Record<string, ListViewMode>;

export const useUserStore = defineStore("userStore", () => {
    const currentUser = ref<AnyUser>(null);
    const currentPreferences = ref<Preferences | null>(null);

    const currentListViewPreferences = useUserLocalStorage<UserListViewPreferences>(
        "user-store-list-view-preferences",
        {},
        currentUser
    );

    const hasSeenUploadHelp = useUserLocalStorage("user-store-seen-upload-help", false, currentUser);

    let loadPromise: Promise<void> | null = null;

    function $reset() {
        currentUser.value = null;
        currentPreferences.value = null;
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
        if (currentPreferences.value?.favorites) {
            return currentPreferences.value.favorites;
        } else {
            return { tools: [] };
        }
    });

    const matchesCurrentUsername = computed(() => {
        return (username?: string) => {
            return isRegisteredUser(currentUser.value) && currentUser.value.username === username;
        };
    });

    function setCurrentUser(user: RegisteredUser) {
        currentUser.value = user;
    }

    function loadUser(includeHistories = true) {
        if (!loadPromise) {
            loadPromise = new Promise<void>((resolve, reject) => {
                (async () => {
                    console.debug("Loading once");
                    try {
                        const user = await getCurrentUser();

                        if (isRegisteredUser(user)) {
                            currentUser.value = user;
                            currentPreferences.value = processUserPreferences(user);
                        } else if (isAnonymousUser(user)) {
                            currentUser.value = user;
                        } else if (user === null) {
                            currentUser.value = null;
                        }
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
        const tools = await addFavoriteToolQuery(currentUser.value.id, toolId);
        setFavoriteTools(tools);
    }

    async function removeFavoriteTool(toolId: string) {
        if (!currentUser.value || currentUser.value.isAnonymous) {
            return;
        }
        const tools = await removeFavoriteToolQuery(currentUser.value.id, toolId);
        setFavoriteTools(tools);
    }

    function setFavoriteTools(tools: string[]) {
        if (currentPreferences.value) {
            currentPreferences.value.favorites.tools = tools;
        }
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
            typeof user.preferences.favorites === "string" ? JSON.parse(user.preferences.favorites) : { tools: [] };
        return {
            ...user.preferences,
            favorites,
        };
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
        loadUser,
        matchesCurrentUsername,
        setCurrentUser,
        setCurrentTheme,
        setListViewPreference,
        addFavoriteTool,
        removeFavoriteTool,
        $reset,
    };
});
