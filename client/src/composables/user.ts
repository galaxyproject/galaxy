import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useUserStore } from "@/stores/userStore";

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
    const { currentUser } = storeToRefs(useUserStore());
    const userTags = computed(() => {
        let tags: string[];
        if (currentUser.value && !currentUser.value.isAnonymous) {
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
