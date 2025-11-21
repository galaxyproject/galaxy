import { createTestingPinia } from "@pinia/testing";

// IMPORTANT: This import MUST come after the mock calls above for proper module hoisting
// eslint-disable-next-line import/order
import { getSelectableObjectStores } from "@/api/objectStores";

// @ts-ignore - vi is a Vitest global
vi.mock("@/api/objectStores");

const OBJECT_STORES = [
    {
        id: "object_store_1",
        object_store_id: "object_store_1",
        badges: [],
        quota: { enabled: false },
        private: false,
        name: "Object Store 1",
    },
    {
        id: "object_store_2",
        object_store_id: "object_store_2",
        badges: [],
        quota: { enabled: false },
        private: false,
        name: "Object Store 2",
    },
];

export function setupSelectableMock() {
    createTestingPinia();
    const mockGetObjectStores = getSelectableObjectStores as any;
    mockGetObjectStores.mockResolvedValue(OBJECT_STORES);
}
