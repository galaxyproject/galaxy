import { computed } from "vue";

import { isDetailedCollection } from "@/api";
import { useDatasetCollectionStore } from "@/stores/datasetCollectionStore";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    collectionId: string;
}

export function useDetailedCollection<T extends Props>(props: T) {
    const collectionStore = useDatasetCollectionStore();

    // `getDetailedCollection` triggers a detail fetch (or upgrade from summary)
    // on first access; while loading or summary-only, the narrow yields null.
    const collection = computed(() => {
        const entry = collectionStore.getDetailedCollection(props.collectionId);
        return isDetailedCollection(entry) ? entry : null;
    });

    // Read the error by id so it surfaces even before `collection` lands.
    const collectionLoadError = computed(() => {
        const err = collectionStore.getCollectionError(props.collectionId);
        return err ? errorMessageAsString(err) : undefined;
    });

    return {
        collectionStore,
        collection,
        collectionLoadError,
    };
}
