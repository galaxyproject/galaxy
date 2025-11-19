import { createTestingPinia } from "@pinia/testing";

// Use vi.mock for Vitest, jest.mock for Jest
// @ts-ignore - These are test globals
if (typeof vi !== "undefined") {
    // Vitest
    // @ts-ignore - vi is a Vitest global
    vi.mock("@/api/objectStores");
} else {
    // Jest
    // @ts-ignore - jest is a Jest global
    jest.mock("@/api/objectStores");
}

import { getSelectableObjectStores } from "@/api/objectStores";

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
    // Support both Jest and Vitest MockedFunction types
    const mockGetObjectStores = getSelectableObjectStores as any;
    mockGetObjectStores.mockResolvedValue(OBJECT_STORES);
}
