import { computed, ref } from "vue";

import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";

export type FavoriteObjectKind = "tags" | "edam_operations" | "edam_topics";

/** Shared favorite actions for curated tags and EDAM terms in cards and filter chips. */
export function useFavoriteObjects() {
    const userStore = useUserStore();
    const toast = useToast();
    const pending = ref(new Set<string>());
    const canFavorite = computed(() => Boolean(userStore.currentUser) && !userStore.isAnonymous);
    const keyFor = (kind: FavoriteObjectKind, value: string) => JSON.stringify([kind, value]);
    const isFavorite = (kind: FavoriteObjectKind, value: string) => userStore.currentFavorites[kind].includes(value);
    const isSaving = (kind: FavoriteObjectKind, value: string) => pending.value.has(keyFor(kind, value));

    async function toggleFavorite(kind: FavoriteObjectKind, value: string, label = value) {
        if (!canFavorite.value) {
            toast.error("You must be signed in to manage favorites.");
            ariaAlert("Sign in to manage favorites");
            return;
        }
        if (isSaving(kind, value)) {
            return;
        }
        const key = keyFor(kind, value);
        const removing = isFavorite(kind, value);
        pending.value.add(key);
        const actions = {
            tags: { add: userStore.addFavoriteTag, remove: userStore.removeFavoriteTag },
            edam_operations: { add: userStore.addFavoriteEdamOperation, remove: userStore.removeFavoriteEdamOperation },
            edam_topics: { add: userStore.addFavoriteEdamTopic, remove: userStore.removeFavoriteEdamTopic },
        };
        try {
            await actions[kind][removing ? "remove" : "add"](value);
            ariaAlert(`${removing ? "Removed" : "Added"} ${label} ${removing ? "from" : "to"} favorites`);
        } catch {
            toast.error(`Failed to update favorite '${label}'.`);
            ariaAlert(`Failed to update favorite ${label}`);
        } finally {
            pending.value.delete(key);
        }
    }

    return { canFavorite, isFavorite, isSaving, toggleFavorite };
}
