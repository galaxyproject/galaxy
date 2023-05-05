import { fetcher } from "@/schema/fetcher";

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
