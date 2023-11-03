/** Contains type alias and definitions related to Galaxy API models. */

import { components } from "@/api/schema";

/**
 * Contains minimal information about a History.
 */
export type HistorySummary = components["schemas"]["HistorySummary"];

/**
 * Contains additional details about a History.
 */
export type HistoryDetailed = components["schemas"]["HistoryDetailed"];

/**
 * Contains minimal information about a HistoryContentItem.
 */
export type HistoryContentItemBase = components["schemas"]["EncodedHistoryContentItem"];

/**
 * Contains summary information about a HistoryDatasetAssociation.
 */
export type DatasetSummary = components["schemas"]["HDASummary"];

/**
 * Contains additional details about a HistoryDatasetAssociation.
 */
export type DatasetDetails = components["schemas"]["HDADetailed"];

/**
 * Represents a HistoryDatasetAssociation with either summary or detailed information.
 */
export type DatasetEntry = DatasetSummary | DatasetDetails;

/**
 * Contains summary information about a DCE (DatasetCollectionElement).
 *
 * DCEs associate a parent collection to its elements. Those elements can be either
 * HDAs or other DCs (DatasetCollections).
 * The type of the element is indicated by the `element_type` field and the element
 * itself is contained in the `object` field.
 */
export type DCESummary = components["schemas"]["DCESummary"];

/**
 * DatasetCollectionElement specific type for collections.
 */
export interface DCECollection extends DCESummary {
    element_type: "dataset_collection";
    object: DCObject;
}

/**
 * Contains summary information about a HDCA (HistoryDatasetCollectionAssociation).
 *
 * HDCAs are (top level only) history items that contains information about the association
 * between a History and a DatasetCollection.
 */
export type HDCASummary = components["schemas"]["HDCASummary"];

/**
 * Contains additional details about a HistoryDatasetCollectionAssociation.
 */
export type HDCADetailed = components["schemas"]["HDCADetailed"];

/**
 * Contains information about a DatasetCollection.
 *
 * DatasetCollections are immutable and contain one or more DCEs.
 */
export type DCObject = components["schemas"]["DCObject"];

export type DatasetCollectionAttributes = components["schemas"]["DatasetCollectionAttributesResult"];

/**
 * A SubCollection is a DatasetCollectionElement of type `dataset_collection`
 * with additional information to simplify its handling.
 *
 * This is used to be able to distinguish between top level HDCAs and sub-collections.
 * It helps simplify both, the representation of sub-collections in the UI, and fetching of elements.
 */
export interface SubCollection extends DCObject {
    /** The name of the collection. Usually corresponds to the DCE identifier. */
    name: string;
    /** The ID of the top level HDCA that associates this collection with the History it belongs to. */
    hdca_id: string;
}

/**
 * Represents either a top level HDCASummary or a sub-collection.
 */
export type CollectionEntry = HDCASummary | SubCollection;

/**
 * Returns true if the given entry is a top level HDCA and false for sub-collections.
 */
export function isHDCA(entry?: CollectionEntry): entry is HDCASummary {
    return (
        entry !== undefined && "history_content_type" in entry && entry.history_content_type === "dataset_collection"
    );
}

/**
 * Returns true if the given element of a collection is a DatasetCollection.
 */
export function isCollectionElement(element: DCESummary): element is DCECollection {
    return element.element_type === "dataset_collection";
}
