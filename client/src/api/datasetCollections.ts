import { type CollectionEntry, type DCESummary, type HDCADetailed, type HDCASummary, isHDCA } from "@/api";
import { fetcher } from "@/api/schema";

const DEFAULT_LIMIT = 50;

const getCollectionDetails = fetcher.path("/api/dataset_collections/{id}").method("get").create();

/**
 * Fetches the details of a collection.
 * @param params.id The ID of the collection (HDCA) to fetch.
 */
export async function fetchCollectionDetails(params: { id: string }): Promise<HDCADetailed> {
    const { data } = await getCollectionDetails({ id: params.id });
    return data as HDCADetailed;
}

/**
 * Fetches the details of a collection.
 * @param params.id The ID of the collection (HDCA) to fetch.
 */
export async function fetchCollectionSummary(params: { id: string }): Promise<HDCASummary> {
    const { data } = await getCollectionDetails({ id: params.id, view: "collection" });
    return data as HDCASummary;
}

const getCollectionContents = fetcher
    .path("/api/dataset_collections/{hdca_id}/contents/{parent_id}")
    .method("get")
    .create();

export async function fetchCollectionElements(params: {
    /** The ID of the top level HDCA that associates this collection with the History it belongs to. */
    hdcaId: string;
    /** The ID of the collection itself. */
    collectionId: string;
    /** The offset to start fetching elements from. */
    offset?: number;
    /** The maximum number of elements to fetch. */
    limit?: number;
}): Promise<DCESummary[]> {
    const { data } = await getCollectionContents({
        instance_type: "history",
        hdca_id: params.hdcaId,
        parent_id: params.collectionId,
        offset: params.offset,
        limit: params.limit,
    });
    return data;
}

export async function fetchElementsFromCollection(params: {
    /** The HDCA or sub-collection to fetch elements from. */
    entry: CollectionEntry;
    /** The offset to start fetching elements from. */
    offset?: number;
    /** The maximum number of elements to fetch. */
    limit?: number;
}): Promise<DCESummary[]> {
    const hdcaId = isHDCA(params.entry) ? params.entry.id : params.entry.hdca_id;
    const collectionId = isHDCA(params.entry) ? params.entry.collection_id : params.entry.id;
    return fetchCollectionElements({
        hdcaId: hdcaId,
        collectionId: collectionId,
        offset: params.offset ?? 0,
        limit: params.limit ?? DEFAULT_LIMIT,
    });
}

export const fetchCollectionAttributes = fetcher
    .path("/api/dataset_collections/{id}/attributes")
    .method("get")
    .create();

const postCopyCollection = fetcher.path("/api/dataset_collections/{id}/copy").method("post").create();
export async function copyCollection(id: string, dbkey: string): Promise<void> {
    await postCopyCollection({ id, dbkey });
}
