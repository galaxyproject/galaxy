import localize from "@/utils/localization";
import { ref } from "vue";
import {
    cleanupDiscardedDatasets,
    fetchDiscardedDatasets,
    fetchDiscardedDatasetsSummary,
    cleanupDiscardedHistories,
    fetchDiscardedHistories,
    fetchDiscardedHistoriesSummary,
} from "../services";
import type { CleanupCategory } from "./model";

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
                    cleanupItems: cleanupDiscardedDatasets,
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
                    cleanupItems: cleanupDiscardedHistories,
                },
            ],
        },
    ]);

    return { cleanupCategories };
}
