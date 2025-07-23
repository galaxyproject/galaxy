import {
    type CollectionElementIdentifiers,
    type CollectionEntry,
    type CreateNewCollectionPayload,
    type DCESummary,
    GalaxyApi,
    type HDCADetailed,
    type HDCASummary,
    isHDCA,
} from "@/api";
import type { components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

const DEFAULT_LIMIT = 50;

export type CollectionType = string;

export type SampleSheetCollectionType =
    | "sample_sheet"
    | "sample_sheet:paired"
    | "sample_sheet:paired_or_unpaired"
    | "sample_sheet:record";
// mirror the python definition here
export type SampleSheetColumnValueT = string | number | boolean;

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

export type NewCollectionOptions = {
    name: string;
    element_identifiers: CollectionElementIdentifiers;
    collection_type: string;
    history_id: string;
    copy_elements?: boolean;
    hide_source_items?: boolean;
};

export function createCollectionPayload(options: NewCollectionOptions): CreateNewCollectionPayload {
    const hideSourceItems = options.hide_source_items === undefined ? true : options.hide_source_items;
    return {
        name: options.name,
        history_id: options.history_id,
        element_identifiers: options.element_identifiers,
        collection_type: options.collection_type,
        instance_type: "history",
        fields: "auto",
        copy_elements: options.copy_elements || true,
        hide_source_items: hideSourceItems,
    } as CreateNewCollectionPayload;
}

export async function createHistoryDatasetCollectionInstanceSimple(options: NewCollectionOptions) {
    const payload = createCollectionPayload(options);
    return createHistoryDatasetCollectionInstanceFull(payload);
}

export async function createHistoryDatasetCollectionInstanceFull(payload: CreateNewCollectionPayload) {
    const { data, error } = await GalaxyApi().POST("/api/dataset_collections", {
        body: payload,
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export type CreateWorkbookForCollectionPayload = components["schemas"]["CreateWorkbookForCollectionApi"];
export type CreateWorkbookPayload = components["schemas"]["CreateWorkbookRequest"];

export async function createWorkbook(payload: CreateWorkbookPayload): Promise<Blob> {
    const { data, error } = await GalaxyApi().POST("/api/sample_sheet_workbook", {
        body: payload,
        parseAs: "blob",
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function createWorkbookForCollection(
    hdca_id: string,
    payload: CreateWorkbookForCollectionPayload
): Promise<Blob> {
    const { data, error } = await GalaxyApi().POST("/api/dataset_collections/{hdca_id}/sample_sheet_workbook", {
        params: { path: { hdca_id: hdca_id } },
        body: payload,
        parseAs: "blob",
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}
