import { computed, onMounted, ref, unref } from "vue";
import type { Ref } from "vue";
import { useUserStore } from "@/stores/userStore";

// TODO: support computed for "noFetch"
/**
 * composable user store wrapper
 * @param noFetch when true, the user will not be fetched from the server
 * @param fetchOnce when true, the user will only be fetched from the server if it is not already in the store
 * @returns currentUser computed
 */
export function useCurrentUser(noFetch: boolean | Ref<boolean> = false, fetchOnce: boolean | Ref<boolean> = false) {
    // TODO: add store typing
    const userStore = useUserStore();
    const currentUser = computed(() => userStore.currentUser);
    const currentFavorites = computed(() => userStore.currentFavorites);
    onMounted(() => {
        if (!unref(noFetch) && !(Object.keys(currentUser).length > 0) && unref(fetchOnce)) {
            userStore.loadUser();
        }
    });
    const addFavoriteTool = async (toolId: string) => {
        await userStore.addFavoriteTool(toolId);
    };
    const removeFavoriteTool = async (toolId: string) => {
        await userStore.removeFavoriteTool(toolId);
    };
    return { currentUser, currentFavorites, addFavoriteTool, removeFavoriteTool };
}

export function useCurrentTheme() {
    const userStore = useUserStore();
    const currentTheme = computed(() => userStore.currentTheme);
    function setCurrentTheme(theme: string) {
        userStore.setCurrentTheme(theme);
    }
    return {
        currentTheme,
        setCurrentTheme,
    };
}

// temporarily stores tags which have not yet been fetched from the backend
const localTags = ref<string[]>([]);

/**
 * Keeps tracks of the tags the current user has used.
 */
export function useUserTags() {
    const { currentUser } = useCurrentUser(true);
    const userTags = computed(() => {
        let tags: string[];
        if (currentUser.value) {
            tags = [...currentUser.value.tags_used, ...localTags.value];
        } else {
            tags = localTags.value;
        }
        const tagSet = new Set(tags);
        return Array.from(tagSet).map((tag) => tag.replace(/^name:/, "#"));
    });
    const addLocalTag = (tag: string) => {
        localTags.value.push(tag);
    };
    return { userTags, addLocalTag };
}
