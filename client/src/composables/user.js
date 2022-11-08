import { computed, onMounted, inject, ref } from "vue";

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

    const userTags = computed(() => {
        let tags;

        if (currentUser.value) {
            tags = [...currentUser.value.tags_used, ...localTags.value];
        } else {
            tags = localTags.value;
        }

        return tags.map((tag) => tag.replace(/^name:/, "#"));
    });

    const addLocalTag = (tag) => {
        localTags.value.push(tag);
    };

    return { userTags, addLocalTag };
}
