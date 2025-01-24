import { createTestingPinia } from "@pinia/testing";

import { getSelectableObjectStores } from "@/api/objectStores";

jest.mock("@/api/objectStores");

const OBJECT_STORES = [
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

export function setupSelectableMock() {
    createTestingPinia();
    const mockGetObjectStores = getSelectableObjectStores as jest.MockedFunction<typeof getSelectableObjectStores>;
    mockGetObjectStores.mockResolvedValue(OBJECT_STORES);
}
