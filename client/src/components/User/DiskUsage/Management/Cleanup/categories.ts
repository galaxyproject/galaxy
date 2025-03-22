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
            name: localize("已丢弃项目"),
            operations: [
                {
                    id: "deleted_datasets",
                    name: localize("已删除的数据集"),
                    description: localize(
                        "当您删除数据集时，它不会立即从磁盘中移除（以便您稍后可以恢复它）。" +
                            "但这意味着它在您永久删除之前仍然占用空间。" +
                            "在这里，您可以快速查找并移除这些数据集以释放一些空间"
                    ),
                    fetchSummary: fetchDiscardedDatasetsSummary,
                    fetchItems: fetchDiscardedDatasets,
                    cleanupItems: cleanupDatasets,
                },
                {
                    id: "deleted_histories",
                    name: localize("已删除的历史"),
                    description: localize(
                        "当您删除历史时，它不会立即从磁盘中移除（以便您稍后可以恢复它）。" +
                            "但这意味着它在您永久删除之前仍然占用空间。" +
                            "在这里，您可以快速查找并移除这些历史以释放一些空间"
                    ),
                    fetchSummary: fetchDiscardedHistoriesSummary,
                    fetchItems: fetchDiscardedHistories,
                    cleanupItems: cleanupHistories,
                },
            ],
        },
        {
            id: "archived_items",
            name: localize("已归档项目"),
            operations: [
                {
                    id: "archived_histories",
                    name: localize("已归档的历史"),
                    description: localize(
                        "归档历史是一种将您重要但不经常使用的历史保存在一旁的好方法。" +
                            "但它们仍然会占用磁盘上的空间。" +
                            "在这里，您可以快速查找并永久移除这些历史以释放一些空间"
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
