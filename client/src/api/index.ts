/** Contains type alias and definitions related to Galaxy API models. */

import { components } from "@/api/schema";

/**
 * Contains minimal information about a History.
 */
export type HistorySummary = components["schemas"]["HistorySummary"];

export interface HistorySummaryExtended extends HistorySummary {
    size: number;
    contents_active: components["schemas"]["HistoryActiveContentCounts"];
    user_id: string;
}

/**
 * Contains additional details about a History.
 */
export type HistoryDetailed = components["schemas"]["HistoryDetailed"];

export type AnyHistory = HistorySummary | HistorySummaryExtended | HistoryDetailed;

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
 * Contains storage (object store, quota, etc..) details for a dataset.
 */
export type DatasetStorageDetails = components["schemas"]["DatasetStorageDetails"];

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

export type ConcreteObjectStoreModel = components["schemas"]["ConcreteObjectStoreModel"];

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

/**
 * Returns true if the given dataset entry is an instance of DatasetDetails.
 */
export function hasDetails(entry: DatasetEntry): entry is DatasetDetails {
    return "peek" in entry;
}

/**
 * Contains dataset metadata information.
 */
export type MetadataFiles = components["schemas"]["MetadataFile"][];

export function isHistorySummary(history: AnyHistory): history is HistorySummary {
    return !("user_id" in history);
}

export function isHistorySummaryExtended(history: AnyHistory): history is HistorySummaryExtended {
    return "contents_active" in history && "user_id" in history;
}

type QuotaUsageResponse = components["schemas"]["UserQuotaUsage"];

export interface User extends QuotaUsageResponse {
    id: string;
    email: string;
    tags_used: string[];
    isAnonymous: false;
    is_admin?: boolean;
    username?: string;
}

export interface AnonymousUser {
    isAnonymous: true;
    username?: string;
    is_admin?: false;
}

export type GenericUser = User | AnonymousUser;

export function isRegisteredUser(user: User | AnonymousUser | null): user is User {
    return !user?.isAnonymous;
}

export function userOwnsHistory(user: User | AnonymousUser | null, history: AnyHistory) {
    return (
        // Assuming histories without user_id are owned by the current user
        (isRegisteredUser(user) && !hasOwner(history)) ||
        (isRegisteredUser(user) && hasOwner(history) && user.id === history.user_id)
    );
}

function hasOwner(history: AnyHistory): history is HistorySummaryExtended {
    return "user_id" in history;
}
