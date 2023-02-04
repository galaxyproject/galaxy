import { computed, onMounted, inject, ref, unref } from "vue";
import type { Ref } from "vue";
import type { Store } from "vuex";

// TODO: support computed for "noFetch"
/**
 * composable user store wrapper
 * @param noFetch when true, the user will not be fetched from the server
 * @param fetchOnce when true, the user will only be fetched from the server if it is not already in the store
 * @returns currentUser computed
 */
export function useCurrentUser(noFetch: boolean | Ref<boolean> = false, fetchOnce: boolean | Ref<boolean> = false) {
    // TODO: add store typing
    const store = inject("store") as Store<unknown>;
    const currentUser = computed(() => store.getters["user/currentUser"]);
    const currentFavorites = computed(() => store.getters["user/currentFavorites"]);
    onMounted(() => {
        if (!unref(noFetch) && !(Object.keys(currentUser).length > 0) && unref(fetchOnce)) {
            store.dispatch("user/loadUser");
        }
    });
    const addFavoriteTool = async (toolId: string) => {
        await store.dispatch("user/addFavoriteTool", toolId);
    };
    const removeFavoriteTool = async (toolId: string) => {
        await store.dispatch("user/removeFavoriteTool", toolId);
    };
    return { currentUser, currentFavorites, addFavoriteTool, removeFavoriteTool };
}

export function useCurrentTheme() {
    const store = inject("store") as Store<unknown>;
    const currentTheme = computed(() => store.getters["user/currentTheme"]);
    function setCurrentTheme(theme: string) {
        store.dispatch("user/setCurrentTheme", theme);
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
