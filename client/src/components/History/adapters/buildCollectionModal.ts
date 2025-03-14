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
import RULE_BASED_COLLECTION_CREATOR from "@/components/Collections/RuleBasedCollectionCreatorModal";

export type CollectionType = "list" | "paired" | "list:paired" | "rules";
export type DatasetPair = {
    forward: HDASummary;
    reverse: HDASummary;
    name: string;
};

export const COLLECTION_TYPE_TO_LABEL: Record<string, string> = {
    list: "list",
    "list:paired": "list of pairs",
    paired: "dataset pair",
};

// stand-in for buildCollection from history-view-edit.js
export async function buildRuleCollectionModal(
    selectedContent: HistoryItemSummary[],
    historyId: string,
    fromRulesInput = false,
    defaultHideSourceItems = true
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
            options = {}
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
