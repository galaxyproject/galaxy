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
    isAnonymous: false;
}

interface AnonymousUser {
    isAnonymous: true;
}

interface Preferences {
    theme: string;
    favorites: { tools: string[] };
}

export const useUserStore = defineStore(
    "userStore",
    () => {
        const toggledSideBar = ref("tools");
        const showActivityBar = ref(false);
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

        function loadUser() {
            if (!loadPromise) {
                loadPromise = getCurrentUser()
                    .then(async (user) => {
                        const historyStore = useHistoryStore();
                        currentUser.value = { ...user, isAnonymous: !user.email };
                        currentPreferences.value = user?.preferences ?? null;
                        // TODO: This is a hack to get around the fact that the API returns a string
                        if (currentPreferences.value?.favorites) {
                            currentPreferences.value.favorites = JSON.parse(
                                user?.preferences?.favorites ?? { tools: [] }
                            );
                        }
                        await historyStore.loadCurrentHistory();
                        // load first few histories for user to start pagination
                        await historyStore.loadHistories();
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
    },
    {
        persist: {
            paths: ["showActivityBar", "toggledSideBar"],
        },
    }
);
