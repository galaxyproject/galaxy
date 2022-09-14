import _l from "utils/localization";
import {
    cleanupDatasets,
    fetchDiscardedDatasets,
    fetchDiscardedDatasetsSummary,
    cleanupHistories,
    fetchDiscardedHistories,
    fetchDiscardedHistoriesSummary,
} from "../services";

export const cleanupCategories = [
    {
        name: _l("Discarded Items"),
        operations: [
            {
                id: "deleted_datasets",
                name: _l("Deleted datasets"),
                description: _l(
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
                name: _l("Deleted histories"),
                description: _l(
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
];
