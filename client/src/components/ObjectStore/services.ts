import { fetcher } from "@/schema/fetcher";

const getObjectStores = fetcher.path("/api/object_store").method("get").create();

export async function getSelectableObjectStores() {
    const { data } = await getObjectStores({ selectable: true });
    return data;
}
