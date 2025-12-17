/**
 * Composable for managing collection creation state and configuration.
 * Handles collection state initialization, updates, and building collection config for upload queue.
 */

import { type Ref, ref } from "vue";

import type { CollectionCreationState } from "@/components/Panels/Upload/types/collectionCreation";
import type { CollectionConfig } from "@/composables/uploadQueue";

export function useCollectionCreation(collectionConfigComponent?: Ref<{ reset: () => void } | null>) {
    const collectionState = ref<CollectionCreationState>({
        config: null,
        validation: {
            isValid: true,
            isActive: false,
            message: "",
        },
    });

    /**
     * Handles collection state changes from the CollectionCreationConfig component
     */
    function handleCollectionStateChange(state: CollectionCreationState) {
        collectionState.value = state;
    }

    /**
     * Builds a CollectionConfig for the upload queue if collection creation is active
     */
    function buildCollectionConfig(targetHistoryId: string): CollectionConfig | undefined {
        if (!collectionState.value.config) {
            return undefined;
        }

        return {
            name: collectionState.value.config.name,
            type: collectionState.value.config.type,
            hideSourceItems: true,
            historyId: targetHistoryId,
        };
    }

    /**
     * Resets the collection configuration component
     */
    function resetCollection() {
        collectionConfigComponent?.value?.reset();
    }

    return {
        collectionState,
        handleCollectionStateChange,
        buildCollectionConfig,
        resetCollection,
    };
}
