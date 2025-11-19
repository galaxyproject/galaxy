import { createTestingPinia } from "@pinia/testing";

import { getSelectableObjectStores } from "@/api/objectStores";

// Use vi.mock for Vitest, jest.mock for Jest
// @ts-ignore - These are test globals
const mockFn = typeof vi !== "undefined" ? vi.mock : jest.mock;
mockFn("@/api/objectStores");

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
