import { fetcher } from "@/schema";

import { DCESummary, HDCASummary } from ".";

const DEFAULT_LIMIT = 50;

const getCollectionContents = fetcher
    .path("/api/dataset_collections/{hdca_id}/contents/{parent_id}")
    .method("get")
    .create();

export async function fetchCollectionElements(params: {
    hdcaId: string;
    collectionId: string;
    offset?: number;
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

export async function fetchElementsFromHDCA(params: {
    hdca: HDCASummary;
    offset?: number;
    limit?: number;
}): Promise<DCESummary[]> {
    return fetchCollectionElements({
        hdcaId: params.hdca.id,
        collectionId: params.hdca.collection_id,
        offset: params.offset ?? 0,
        limit: params.limit ?? DEFAULT_LIMIT,
    });
}
