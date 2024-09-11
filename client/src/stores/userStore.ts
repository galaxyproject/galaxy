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

type ListViewMode = "grid" | "list";

export const useUserStore = defineStore("userStore", () => {
    const currentUser = ref<AnyUser>(null);
    const currentPreferences = ref<Preferences | null>(null);

    // explicitly pass current User, because userStore might not exist yet
    const toggledSideBar = useUserLocalStorage("user-store-toggled-side-bar", "tools", currentUser);
    const preferredListViewMode = useUserLocalStorage("user-store-preferred-list-view-mode", "grid", currentUser);

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
            loadPromise = getCurrentUser()
                .then(async (user) => {
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
                        // load first few histories for user to start pagination
                        await historyStore.loadHistories();
                    }
                })
                .catch((e) => {
                    console.error("Failed to load user", e);
                })
                .finally(() => {
                    loadPromise = null;
                });
        }
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

    function setPreferredListViewMode(view: ListViewMode) {
        preferredListViewMode.value = view;
    }

    function toggleSideBar(currentOpen = "") {
        toggledSideBar.value = toggledSideBar.value === currentOpen ? "" : currentOpen;
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
        toggledSideBar,
        preferredListViewMode,
        loadUser,
        matchesCurrentUsername,
        setCurrentUser,
        setCurrentTheme,
        setPreferredListViewMode,
        addFavoriteTool,
        removeFavoriteTool,
        toggleSideBar,
        $reset,
    };
});
