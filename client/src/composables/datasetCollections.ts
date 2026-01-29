import { computed } from "vue";

import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    collectionId: string;
}

export function useDetailedCollection<T extends Props>(props: T) {
    const collectionStore = useCollectionElementsStore();

    const collection = computed(() => {
        return collectionStore.getDetailedCollectionById(props.collectionId);
    });
    const collectionLoadError = computed(() => {
        if (collection.value) {
            const collectionElementLoadError = collectionStore.getLoadingCollectionElementsError(collection.value);
            if (collectionElementLoadError) {
                return errorMessageAsString(collectionElementLoadError);
            }
        }
        return undefined;
    });
    return {
        collectionStore,
        collection,
        collectionLoadError,
    };
}
