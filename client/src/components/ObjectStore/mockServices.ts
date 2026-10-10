import { createTestingPinia } from "@pinia/testing";
import { vi } from "vitest";

import { getSelectableObjectStores } from "@/api/objectStores";

import { SELECTABLE_OBJECT_STORES } from "./test_fixtures";

vi.mock("@/api/objectStores");

export function setupSelectableMock() {
    createTestingPinia({ createSpy: vi.fn });
    const mockGetObjectStores = getSelectableObjectStores as any;
    mockGetObjectStores.mockResolvedValue(SELECTABLE_OBJECT_STORES);
}
