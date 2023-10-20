import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { components } from "@/schema";
import { useHistoryStore } from "@/stores/historyStore";
import {
    addFavoriteToolQuery,
    getCurrentUser,
    removeFavoriteToolQuery,
    setCurrentThemeQuery,
} from "@/stores/users/queries";
import { expand } from "rxjs";


type DetailedAnonymousUser = components["schemas"]["AnonUserModel"]
type DetailedUserModelUser = components["schemas"]["DetailedUserModel"]

interface AnonymousUser extends DetailedAnonymousUser {
    isAnonymous: true
}

interface User extends DetailedUserModelUser {
    isAnonymous: false;
}
interface Preferences {
    theme: string;
    favorites: { tools: string[] };
}

export const useUserStore = defineStore("userStore", () => {
    const toggledSideBar = useUserLocalStorage("user-store-toggled-side-bar", "tools");
    const showActivityBar = useUserLocalStorage("user-store-show-activity-bar", false);
    const currentUser = ref<User | AnonymousUser | null>(null);
    const currentPreferences = ref<Preferences | null>(null);

    let loadPromise: Promise<void> | null = null;

    const isAnonymous = computed(() => {
        return !("email" in (currentUser.value || []));
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

    function setCurrentUser(user: User) {
        currentUser.value = user;
    }

    function loadUser(includeHistories = true) {
        if (!loadPromise) {
            loadPromise = getCurrentUser()
                .then(async (user) => {
                    if ('email' in user) {
                        currentUser.value = { ...user, isAnonymous: false };
                        currentPreferences.value = user.preferences as unknown as Preferences;
                    }
                    else {
                        currentUser.value = { ...user, isAnonymous: true };
                        currentPreferences.value = null;
                    }
                    // TODO: This is a hack to get around the fact that the API returns a string
                    if (currentPreferences.value?.favorites && isRegisteredUser(user)) {
                        currentPreferences.value.favorites = JSON.parse(user?.preferences?.favorites ?? { tools: [] });
                    }
                    if (includeHistories) {
                        const historyStore = useHistoryStore();
                        await historyStore.loadCurrentHistory();
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
    function isRegisteredUser(user?: any): user is User {
        return (
            user !== undefined && "email" in user
        );
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
            currentPreferences.value.favorites.tools = tools ?? { tools: [] };
        }
    }

    function toggleActivityBar() {
        showActivityBar.value = !showActivityBar.value;
    }
    function toggleSideBar(currentOpen = "") {
        toggledSideBar.value = toggledSideBar.value === currentOpen ? "" : currentOpen;
    }

    return {
        currentUser,
        currentPreferences,
        isAnonymous,
        currentTheme,
        currentFavorites,
        showActivityBar,
        toggledSideBar,
        loadUser,
        setCurrentUser,
        setCurrentTheme,
        addFavoriteTool,
        removeFavoriteTool,
        toggleActivityBar,
        toggleSideBar,
    };
});
