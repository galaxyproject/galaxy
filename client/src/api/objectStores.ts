import { fetcher } from "@/api/schema";
import type { components } from "@/api/schema/schema";

export type UserConcreteObjectStore = components["schemas"]["UserConcreteObjectStoreModel"];

export type ObjectStoreTemplateType = "aws_s3" | "azure_blob" | "boto3" | "disk" | "generic_s3";

const getObjectStores = fetcher.path("/api/object_stores").method("get").create();

export async function getSelectableObjectStores() {
    const { data } = await getObjectStores({ selectable: true });
    return data;
}

const getObjectStore = fetcher.path("/api/object_stores/{object_store_id}").method("get").create();
const getUserObjectStoreInstance = fetcher
    .path("/api/object_store_instances/{user_object_store_id}")
    .method("get")
    .create();

export async function getObjectStoreDetails(id: string) {
    if (id.startsWith("user_objects://")) {
        const userObjectStoreId = id.substring("user_objects://".length);
        const { data } = await getUserObjectStoreInstance({ user_object_store_id: userObjectStoreId });
        return data;
    } else {
        const { data } = await getObjectStore({ object_store_id: id });
        return data;
    }
}

const updateObjectStoreFetcher = fetcher.path("/api/datasets/{dataset_id}/object_store_id").method("put").create();

export async function updateObjectStore(datasetId: string, objectStoreId: string) {
    const { data } = await updateObjectStoreFetcher({ dataset_id: datasetId, object_store_id: objectStoreId });
    return data;
}
