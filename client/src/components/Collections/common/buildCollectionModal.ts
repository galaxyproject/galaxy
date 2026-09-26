/**
 * Launch bootstrap modals with Vue components, for use with the collection assembly modals.
 * i.e. With selected..... create dataset collection, create paired collection, etc.
 */

import type { HDASummary, HistoryItemSummary } from "@/api";
import type { CollectionType } from "@/api/datasetCollections";
import { createCollectionViaRules } from "@/components/Collections/RuleBasedCollectionCreatorModal";
import { createDatasetCollection } from "@/components/History/model/queries";
import { useHistoryStore } from "@/stores/historyStore";

// This is type describes builders we know about - not valid "collection type"s
// as the backend/model layer of Galaxy would understand them. Rules is a collection
// builder but not a collection type, paired:paired:list is a valid collection type but
// not something we would ever make a builder for.
export type CollectionBuilderType =
    | "list"
    | "paired"
    | "list:paired"
    | "rules"
    | "list:paired_or_unpaired"
    | "list:list"
    | "list:list:paired"
    | "sample_sheet"
    | "sample_sheet:paired"
    | "sample_sheet:paired_or_unpaired"
    | "sample_sheet:record";

interface HasName {
    name: string | null;
}

export type GenericPair<T extends HasName> = {
    forward: T;
    reverse: T;
    name: string;
};

export const COLLECTION_TYPE_TO_LABEL: Record<string, string> = {
    list: "list",
    "list:paired": "list of pairs",
    "list:paired_or_unpaired": "mixed list of paired and unpaired",
    paired: "dataset pair",
    sample_sheet: "sample sheet derived",
};

export type DatasetPair = GenericPair<HDASummary>;

export async function buildCollectionFromRules(
    selection: any,
    historyId: string | null = null,
    fromRulesInput = false,
) {
    let selectionContent: any = null;
    const { loadCurrentHistoryId } = useHistoryStore();
    historyId = historyId || (await loadCurrentHistoryId());

    if (fromRulesInput) {
        selectionContent = selection;
    } else {
        selectionContent = new Map();
        selection.models.forEach((obj: any) => {
            selectionContent.set(obj.id, obj);
        });
    }
    if (historyId) {
        const content = fromRulesInput ? selectionContent : createContent(historyId, selectionContent);
        const modalResult = await createCollectionViaRules(content);
        if (modalResult) {
            console.debug("Submitting collection build request.", modalResult);
            await createDatasetCollection({ id: historyId } as any, modalResult);
        }
    }
}

const createContent = (historyId: string, selection: HistoryItemSummary[], defaultHideSourceItems: boolean = true) => {
    const selectionJson = Array.from(selection.values());
    return {
        historyId,
        toJSON: () => selectionJson,
        async createHDCA(
            element_identifiers: any,
            collection_type: CollectionType,
            name: string,
            hide_source_items: boolean,
            options = {},
        ) {
            return {
                collection_type,
                name,
                hide_source_items,
                element_identifiers,
                options,
            };
        },
        defaultHideSourceItems,
    };
};
