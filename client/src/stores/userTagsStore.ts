import { defineStore, storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useUserStore } from "./userStore";

export const useUserTagsStore = defineStore("userTagsStore", () => {
    const localTags = ref<string[]>([]);

    const { currentUser } = storeToRefs(useUserStore());

    const userTags = computed(() => {
        let tags: string[];
        if (currentUser.value && !currentUser.value.isAnonymous) {
            tags = [...(currentUser.value.tags_used ?? []), ...localTags.value];
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
});
