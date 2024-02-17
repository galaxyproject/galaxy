import { fetcher } from "@/api/schema";

const getObjectStores = fetcher.path("/api/object_stores").method("get").create();

export async function getSelectableObjectStores() {
    const { data } = await getObjectStores({ selectable: true });
    return data;
}

const getObjectStore = fetcher.path("/api/object_stores/{object_store_id}").method("get").create();

export async function getObjectStoreDetails(id: string) {
    const { data } = await getObjectStore({ object_store_id: id });
    return data;
}

const updateObjectStoreFetcher = fetcher.path("/api/datasets/{dataset_id}/object_store_id").method("put").create();

export async function updateObjectStore(datasetId: string, objectStoreId: string) {
    const { data } = await updateObjectStoreFetcher({ dataset_id: datasetId, object_store_id: objectStoreId });
    return data;
}
