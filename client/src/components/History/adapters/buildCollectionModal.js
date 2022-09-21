/**
 * Temporary adapter to launch bootstrap modals from Vue components, for use with
 * the collection assembly modals. i.e. With selected..... create dataset collection,
 * create paired collection, etc.
 *
 * The goal is to use the existing "createListCollection", etc. functions but doctor
 * the content parameter to have the API of a backbone model which requires a
 * deprecated jquery Deferred object.
 */

import jQuery from "jquery";
import LIST_COLLECTION_CREATOR from "components/Collections/ListCollectionCreatorModal";
import PAIR_COLLECTION_CREATOR from "components/Collections/PairCollectionCreatorModal";
import LIST_OF_PAIRS_COLLECTION_CREATOR from "components/Collections/PairedListCollectionCreatorModal";
import RULE_BASED_COLLECTION_CREATOR from "components/Collections/RuleBasedCollectionCreatorModal";

// stand-in for buildCollection from history-view-edit.js
export async function buildCollectionModal(collectionType, selectedContent, historyId, fromRulesInput = false) {
    // select legacy function
    let createFunc;
    if (collectionType == "list") {
        createFunc = LIST_COLLECTION_CREATOR.createListCollection;
    } else if (collectionType == "paired") {
        createFunc = PAIR_COLLECTION_CREATOR.createPairCollection;
    } else if (collectionType == "list:paired") {
        createFunc = LIST_OF_PAIRS_COLLECTION_CREATOR.createPairedListCollection;
    } else if (collectionType.startsWith("rules")) {
        createFunc = RULE_BASED_COLLECTION_CREATOR.createCollectionViaRules;
    } else {
        throw new Error(`Unknown collectionType encountered ${collectionType}`);
    }
    // pull up cached content by type_ids;
    if (fromRulesInput) {
        return await createFunc(selectedContent);
    } else {
        const fakeBackboneContent = createBackboneContent(historyId, selectedContent);
        return await createFunc(fakeBackboneContent);
    }
}

const createBackboneContent = (historyId, selection) => {
    const selectionJson = Array.from(selection.values());
    return {
        historyId,
        toJSON: () => selectionJson,
        // result must be a $.Deferred object instead of a promise because
        // that's the kind of deprecated data format that backbone likes to use.
        createHDCA(element_identifiers, collection_type, name, hide_source_items, copy_elements, options = {}) {
            const def = jQuery.Deferred();
            return def.resolve(null, {
                collection_type,
                name,
                copy_elements,
                hide_source_items,
                element_identifiers,
                options,
            });
        },
    };
};
