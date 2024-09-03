import { ref } from "vue";

import localize from "@/utils/localization";

import {
    cleanupDatasets,
    cleanupHistories,
    fetchArchivedHistories,
    fetchArchivedHistoriesSummary,
    fetchDiscardedDatasets,
    fetchDiscardedDatasetsSummary,
    fetchDiscardedHistories,
    fetchDiscardedHistoriesSummary,
} from "../services";
import { type CleanupCategory } from "./model";

export function useCleanupCategories() {
    const cleanupCategories = ref<CleanupCategory[]>([
        {
            id: "discarded_items",
            name: localize("Discarded Items"),
            operations: [
                {
                    id: "deleted_datasets",
                    name: localize("Deleted datasets"),
                    description: localize(
                        "When you delete a dataset it's not immediately removed from the disk (so you can recover it later)." +
                            " But this means it's still taking space until you permanently delete it." +
                            " Here you can quickly find and remove those datasets to free up some space"
                    ),
                    fetchSummary: fetchDiscardedDatasetsSummary,
                    fetchItems: fetchDiscardedDatasets,
                    cleanupItems: cleanupDatasets,
                },
                {
                    id: "deleted_histories",
                    name: localize("Deleted histories"),
                    description: localize(
                        "When you delete a history it's not immediately removed from the disk (so you can recover it later)." +
                            " But this means it's still taking space until you permanently delete it." +
                            " Here you can quickly find and remove those histories to free up some space"
                    ),
                    fetchSummary: fetchDiscardedHistoriesSummary,
                    fetchItems: fetchDiscardedHistories,
                    cleanupItems: cleanupHistories,
                },
            ],
        },
        {
            id: "archived_items",
            name: localize("Archived Items"),
            operations: [
                {
                    id: "archived_histories",
                    name: localize("Archived histories"),
                    description: localize(
                        "Archived histories are a good way to keep some of your important but not frequently used histories out of the way." +
                            " But they can still take up space on the disk." +
                            " Here you can quickly find and permanently remove those histories to free up some space"
                    ),
                    fetchSummary: fetchArchivedHistoriesSummary,
                    fetchItems: fetchArchivedHistories,
                    cleanupItems: cleanupHistories,
                },
            ],
        },
    ]);

    return { cleanupCategories };
}
