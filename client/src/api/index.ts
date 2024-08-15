/** Contains type alias and definitions related to Galaxy API models. */

import { type components } from "@/api/schema";

/**
 * Contains minimal information about a History.
 */
export type HistorySummary = components["schemas"]["HistorySummary"];

/**
 * Contains minimal information about a History with additional content stats.
 * This is a subset of information that can be relatively frequently updated after
 * certain actions are performed on the history.
 */
export interface HistoryContentsStats {
    id: string;
    update_time: string;
    size: number;
    contents_active: components["schemas"]["HistoryActiveContentCounts"];
}

/**
 * Contains summary information plus additional details about the contents and owner of a History.
 * This is used by the client API to simplify the handling of History objects.
 *
 * Data returned by the API when requesting `?view=summary&keys=size,contents_active,user_id`.
 */
export interface HistorySummaryExtended extends HistorySummary, HistoryContentsStats {
    /** The ID of the user that owns the history. Null if the history is owned by an anonymous user. */
    user_id: string | null;
}

type HistoryDetailedModel = components["schemas"]["HistoryDetailed"];

/**
 * Contains additional details about a History.
 *
 * Data returned by the API when requesting `?view=detailed`.
 */
export interface HistoryDetailed extends HistoryDetailedModel {
    // TODO: these fields are not present in the backend schema model `HistoryDetailedModel` but are serialized by the API
    // when requesting ?view=detailed. We should consider adding them to the backend schema.
    email_hash?: string;
    empty: boolean;
    hid_counter: number;
}

type HistoryDetailedCommon = Omit<
    HistoryDetailed,
    "username" | "state" | "state_ids" | "state_details" | "email_hash" | "empty"
>;

/**
 * Alternative representation of history details used by the client API.
 * Shares most of the fields with HistoryDetailed but not all and adds some additional fields.
 *
 * Data returned by the API when requesting `?view=dev-detailed`.
 */
export interface HistoryDevDetailed extends HistoryDetailedCommon {
    contents_active: components["schemas"]["HistoryActiveContentCounts"];
}

/**
 * Contains all available information about a History.
 */
export type HistoryExtended = HistoryDevDetailed & HistoryDetailed;

/**
 * Represents any amount of information about a History with the minimal being a HistorySummary.
 */
export type AnyHistory =
    | HistorySummary
    | HistorySummaryExtended
    | HistoryDetailed
    | HistoryDevDetailed
    | HistoryExtended;

/**
 * Contains minimal information about a HistoryContentItem.
 */
export type HistoryContentItemBase = components["schemas"]["EncodedHistoryContentItem"];

/**
 * Contains summary information about a HistoryDatasetAssociation.
 */
export type HDASummary = components["schemas"]["HDASummary"];

/**
 * Contains additional details about a HistoryDatasetAssociation.
 */
export type HDADetailed = components["schemas"]["HDADetailed"];

/**
 * Represents either an HDA or an HDCA with minimal information.
 */
export type HistoryItemSummary = HDASummary | HDCASummary;

/**
 * Represents a HistoryDatasetAssociation that is inaccessible to the user.
 */
export type HDAInaccessible = components["schemas"]["HDAInaccessible"];

/**
 * Contains storage (object store, quota, etc..) details for a dataset.
 */
export type DatasetStorageDetails = components["schemas"]["DatasetStorageDetails"];

/**
 * Represents a HistoryDatasetAssociation with either summary or detailed information.
 */
export type DatasetEntry = HDASummary | HDADetailed | HDAInaccessible;

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
export function hasDetails(entry: DatasetEntry): entry is HDADetailed {
    return "peek" in entry;
}

export function isInaccessible(entry: DatasetEntry): entry is HDAInaccessible {
    return "accessible" in entry && !entry.accessible;
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

export function isHistoryItem(item: object): item is HistoryItemSummary {
    return item && "history_content_type" in item;
}

type RegisteredUserModel = components["schemas"]["DetailedUserModel"];
type AnonymousUserModel = components["schemas"]["AnonUserModel"];
type UserModel = RegisteredUserModel | AnonymousUserModel;

export interface RegisteredUser extends RegisteredUserModel {
    isAnonymous: false;
}

export interface AnonymousUser extends AnonymousUserModel {
    isAnonymous: true;
}

/** Represents any user, including anonymous users or session-less (null) users.**/
export type AnyUser = RegisteredUser | AnonymousUser | null;

export function isRegisteredUser(user: AnyUser | UserModel): user is RegisteredUser {
    return user !== null && "email" in user;
}

export function isAnonymousUser(user: AnyUser | UserModel): user is AnonymousUser {
    return user !== null && !isRegisteredUser(user);
}

export function isAdminUser(user: AnyUser | UserModel): user is RegisteredUser {
    return isRegisteredUser(user) && user.is_admin;
}

export function userOwnsHistory(user: AnyUser, history: AnyHistory) {
    return (
        // Assuming histories without user_id are owned by the current user
        (isRegisteredUser(user) && !hasOwner(history)) ||
        (isRegisteredUser(user) && hasOwner(history) && user.id === history.user_id) ||
        (isAnonymousUser(user) && hasAnonymousOwner(history))
    );
}

function hasOwner(history: AnyHistory): history is HistorySummaryExtended {
    return "user_id" in history && history.user_id !== null;
}

function hasAnonymousOwner(history: AnyHistory): history is HistorySummaryExtended {
    return "user_id" in history && history.user_id === null;
}

export function canMutateHistory(history: AnyHistory): boolean {
    return !history.purged && !history.archived;
}

export type DatasetHash = components["schemas"]["DatasetHash"];

export type DatasetTransform = {
    action: "to_posix_lines" | "spaces_to_tabs" | "datatype_groom";
    datatype_ext: "bam" | "qname_sorted.bam" | "qname_input_sorted.bam" | "isa-tab" | "isa-json";
};
