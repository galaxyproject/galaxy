/**
 * TODO: Update this description...
 * Temporary adapter to launch bootstrap modals from Vue components, for use with
 * the collection assembly modals. i.e. With selected..... create dataset collection,
 * create paired collection, etc.
 *
 * The goal is to use the existing "createListCollection", etc. functions but doctor
 * the content parameter to have the API of a backbone model which requires a
 * deprecated jquery Deferred object.
 */

import jQuery from "jquery";

import type { HDASummary, HistoryItemSummary } from "@/api";
import type { CollectionType } from "@/api/datasetCollections";
import RULE_BASED_COLLECTION_CREATOR from "@/components/Collections/RuleBasedCollectionCreatorModal";
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
        const modalResult = await buildRuleCollectionModal(selectionContent, historyId, fromRulesInput);
        if (modalResult) {
            console.debug("Submitting collection build request.", modalResult);
            await createDatasetCollection({ id: historyId } as any, modalResult);
        }
    }
}

// stand-in for buildCollection from history-view-edit.js
export async function buildRuleCollectionModal(
    selectedContent: HistoryItemSummary[],
    historyId: string,
    fromRulesInput = false,
    defaultHideSourceItems = true,
) {
    // select legacy function
    const createFunc = RULE_BASED_COLLECTION_CREATOR.createCollectionViaRules;
    // pull up cached content by type_ids;
    if (fromRulesInput) {
        return await createFunc(selectedContent);
    } else {
        const fakeBackboneContent = createBackboneContent(historyId, selectedContent, defaultHideSourceItems);
        return await createFunc(fakeBackboneContent);
    }
}

const createBackboneContent = (historyId: string, selection: HistoryItemSummary[], defaultHideSourceItems: boolean) => {
    const selectionJson = Array.from(selection.values());
    return {
        historyId,
        toJSON: () => selectionJson,
        // result must be a $.Deferred object instead of a promise because
        // that's the kind of deprecated data format that backbone likes to use.
        createHDCA(
            element_identifiers: any,
            collection_type: CollectionType,
            name: string,
            hide_source_items: boolean,
            options = {},
        ) {
            const def = jQuery.Deferred();
            return def.resolve(null, {
                collection_type,
                name,
                hide_source_items,
                element_identifiers,
                options,
            });
        },
        defaultHideSourceItems,
    };
};
