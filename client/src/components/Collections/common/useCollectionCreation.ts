import { storeToRefs } from "pinia";

import {
    type CollectionElementIdentifiers,
    createCollectionPayload,
    type CreateNewCollectionPayload,
} from "@/api/datasetCollections";
import { useHistoryStore } from "@/stores/historyStore";

export function useCollectionCreation() {
    const historyStore = useHistoryStore();
    const { currentHistoryId } = storeToRefs(historyStore);

    function createPayload(
        name: string,
        collection_type: string,
        element_identifiers: CollectionElementIdentifiers,
        hide_source_items: boolean
    ): CreateNewCollectionPayload {
        return createCollectionPayload({
            name: name,
            collection_type: collection_type,
            element_identifiers: element_identifiers,
            hide_source_items: hide_source_items,
            history_id: currentHistoryId.value || "current",
        });
    }

    return {
        currentHistoryId,
        createPayload,
    };
}
