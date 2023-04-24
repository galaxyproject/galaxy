import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { useHistoryStore } from "@/stores/historyStore";
import {
    addFavoriteToolQuery,
    removeFavoriteToolQuery,
    getCurrentUser,
    setCurrentThemeQuery,
} from "@/stores/users/queries";

interface User {
    id: string;
    email: string;
    tags_used: string[];
}

interface Preferences {
    theme: string;
    favorites: { tools: string[] };
}

export const useUserStore = defineStore(
    "userStore",
    () => {
        const toggledSideBar = ref("search");
        const toggledActivityBar = ref(false);
        const currentUser = ref<User | null>(null);
        const currentPreferences = ref<Preferences | null>(null);

        let loadPromise: Promise<void> | null = null;

        const isAnonymous = computed(() => {
            return !currentUser.value?.email;
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

        function loadUser() {
            if (!loadPromise) {
                loadPromise = getCurrentUser()
                    .then((user) => {
                        const historyStore = useHistoryStore();
                        currentUser.value = { ...user, isAnonymous: !user.email };
                        currentPreferences.value = user?.preferences ?? null;
                        // TODO: This is a hack to get around the fact that the API returns a string
                        if (currentPreferences.value?.favorites) {
                            currentPreferences.value.favorites = JSON.parse(
                                user?.preferences?.favorites ?? { tools: [] }
                            );
                        }
                        historyStore.loadCurrentHistory();
                        historyStore.loadHistories();
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
            if (!currentUser.value) {
                return;
            }
            const currentTheme = await setCurrentThemeQuery(currentUser.value.id, theme);
            if (currentPreferences.value) {
                currentPreferences.value.theme = currentTheme;
            }
        }
        async function addFavoriteTool(toolId: string) {
            if (!currentUser.value) {
                return;
            }
            const tools = await addFavoriteToolQuery(currentUser.value.id, toolId);
            setFavoriteTools(tools);
        }

        async function removeFavoriteTool(toolId: string) {
            if (!currentUser.value) {
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
            toggledActivityBar.value = !toggledActivityBar.value;
        }
        function toggleSideBar(currentOpen: string) {
            toggledSideBar.value = toggledSideBar.value === currentOpen ? "" : currentOpen;
        }

        return {
            currentUser,
            currentPreferences,
            isAnonymous,
            currentTheme,
            currentFavorites,
            loadUser,
            setCurrentUser,
            setCurrentTheme,
            addFavoriteTool,
            removeFavoriteTool,
            toggleActivityBar,
            toggleSideBar,
        };
    },
    {
        persist: {
            paths: ["toggledActivityBar", "toggledSideBar"],
        },
    }
);
