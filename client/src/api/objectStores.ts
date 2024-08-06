import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type UserConcreteObjectStore = components["schemas"]["UserConcreteObjectStoreModel"];

export type ObjectStoreTemplateType = components["schemas"]["UserConcreteObjectStoreModel"]["type"];

export async function getSelectableObjectStores() {
    const { data, error } = await GalaxyApi().GET("/api/object_stores", {
        params: {
            query: { selectable: true },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function getObjectStoreDetails(id: string) {
    if (id.startsWith("user_objects://")) {
        const userObjectStoreId = id.substring("user_objects://".length);

        const { data, error } = await GalaxyApi().GET("/api/object_store_instances/{user_object_store_id}", {
            params: { path: { user_object_store_id: userObjectStoreId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        return data;
    } else {
        const { data, error } = await GalaxyApi().GET("/api/object_stores/{object_store_id}", {
            params: { path: { object_store_id: id } },
        });

        if (error) {
            rethrowSimple(error);
        }

        return data;
    }
}

export async function updateObjectStore(datasetId: string, objectStoreId: string) {
    const { error } = await GalaxyApi().PUT("/api/datasets/{dataset_id}/object_store_id", {
        params: { path: { dataset_id: datasetId } },
        body: { object_store_id: objectStoreId },
    });

    if (error) {
        rethrowSimple(error);
    }
}
