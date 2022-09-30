import { computed, onMounted, inject, watch, ref } from "vue";

/**
 * composable user store wrapper
 * @returns currentUser computed
 */
export function useCurrentUser() {
    const store = inject("store");

    const currentUser = computed(() => store.getters["user/currentUser"]);

    onMounted(() => {
        store.dispatch("user/loadUser");
    });

    const addFavoriteTool = async (toolId) => await store.dispatch("user/addFavoriteTool", toolId);
    const removeFavoriteTool = async (toolId) => await store.dispatch("user/removeFavoriteTool", toolId);

    return { currentUser, addFavoriteTool, removeFavoriteTool };
}

// temporarily stores tags which have not yet been fetched from the backend
const localTags = ref([]);

/**
 * Keeps tracks of the tags the current user has used.
 */
export function useUserTags() {
    const { currentUser } = useCurrentUser();

    watch(
        () => currentUser.value,
        (user) => {
            // reset local tags if user reloads
            if (user) {
                localTags.value = [];
            }
        }
    );

    const userTags = computed(() => {
        if (currentUser.value) {
            return [...currentUser.value.tags_used, ...localTags.value];
        } else {
            return localTags.value;
        }
    });

    const addLocalTag = (tag) => {
        localTags.value.push(tag);
    };

    return { userTags, addLocalTag };
}
