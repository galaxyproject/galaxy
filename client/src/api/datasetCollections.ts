import { type CollectionEntry, type DCESummary, GalaxyApi, type HDCADetailed, type HDCASummary, isHDCA } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

const DEFAULT_LIMIT = 50;

/**
 * Fetches the details of a collection.
 * @param params.id The ID of the collection (HDCA) to fetch.
 */
export async function fetchCollectionDetails(params: { hdca_id: string }): Promise<HDCADetailed> {
    const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{hdca_id}", {
        params: { path: params },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data as HDCADetailed;
}

/**
 * Fetches the details of a collection.
 * @param params.id The ID of the collection (HDCA) to fetch.
 */
export async function fetchCollectionSummary(params: { hdca_id: string }): Promise<HDCASummary> {
    const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{hdca_id}", {
        params: {
            path: params,
            query: { view: "collection" },
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data as HDCASummary;
}

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
    const { data, error } = await GalaxyApi().GET("/api/dataset_collections/{hdca_id}/contents/{parent_id}", {
        params: {
            path: { hdca_id: params.hdcaId, parent_id: params.collectionId },
            query: { instance_type: "history", offset: params.offset, limit: params.limit },
        },
    });

    if (error) {
        rethrowSimple(error);
    }
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
