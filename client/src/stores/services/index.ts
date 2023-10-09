import { components } from "@/schema";

/** Minimal representation of a collection that can contain datasets or other collections.
 *
 * This is used as a common interface to be able to fetch the contents of a collection regardless
 * of whether it is an HDCA (top level) or a nested collection (DCO).
 *
 * To convert a DCO to a CollectionEntry we need the parent HDCA ID and the name of the
 * collection (DCE identifier). The collection_id is the ID of the DCO and collection_type as well.
 */
export interface CollectionEntry {
    /**HDCA ID */
    id: string;
    /**DCO ID */
    collection_id: string;
    /**Name of the HDCA or DatasetCollectionElement identifier */
    name: string;
    /**Type of the collection */
    collection_type: string;
}

export type DatasetSummary = components["schemas"]["HDASummary"];
export type DatasetDetails = components["schemas"]["HDADetailed"];
export type DCESummary = components["schemas"]["DCESummary"];
export type HDCASummary = components["schemas"]["HDCASummary"] & CollectionEntry;
export type HDCADetailed = components["schemas"]["HDCADetailed"];
export type DCObject = components["schemas"]["DCObject"];

export type HistoryContentItemBase = components["schemas"]["EncodedHistoryContentItem"];

export type DatasetEntry = DatasetSummary | DatasetDetails;
