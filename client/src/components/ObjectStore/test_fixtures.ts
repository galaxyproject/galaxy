import type { ConcreteObjectStoreModel } from "@/api";
import { http } from "@/api/client/__mocks__/http";

/** Two plain selectable storage locations: no badges, no quota, not private. */
export const SELECTABLE_OBJECT_STORES: ConcreteObjectStoreModel[] = [
    {
        object_store_id: "object_store_1",
        badges: [],
        quota: { enabled: false },
        private: false,
        name: "Object Store 1",
    },
    {
        object_store_id: "object_store_2",
        badges: [],
        quota: { enabled: false },
        private: false,
        name: "Object Store 2",
    },
];

/** Answers the request for the storage locations a user may select. */
export function selectableObjectStores(objectStores: ConcreteObjectStoreModel[] = SELECTABLE_OBJECT_STORES) {
    return http.get("/api/object_stores", ({ response }) => response(200).json(objectStores));
}
