import { getSelectableObjectStores } from "./services";
jest.mock("./services");

const OBJECT_STORES = [
    { object_store_id: "object_store_1", badges: [], quota: { enabled: false }, private: false },
    { object_store_id: "object_store_2", badges: [], quota: { enabled: false }, private: false },
];

export function setupSelectableMock() {
    const mockGetObjectStores = getSelectableObjectStores as jest.MockedFunction<typeof getSelectableObjectStores>;
    mockGetObjectStores.mockResolvedValue(OBJECT_STORES);
}
