import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDatatypesMapper } from "@/components/Datatypes";
import { DatatypesMapperModel } from "@/components/Datatypes/model";

import { useDatatypesMapperStore } from "./datatypesMapperStore";

vi.mock("@/components/Datatypes", () => ({
    getDatatypesMapper: vi.fn(),
}));

const mockGetDatatypesMapper = vi.mocked(getDatatypesMapper);

const MAPPER = new DatatypesMapperModel({
    datatypes: ["tabular"],
    datatypes_mapping: {
        ext_to_class_name: { tabular: "galaxy.datatypes.tabular.Tabular" },
        class_to_classes: { "galaxy.datatypes.tabular.Tabular": { "galaxy.datatypes.tabular.Tabular": true } },
    },
});

describe("datatypesMapperStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockGetDatatypesMapper.mockReset();
    });

    it("shares one request between concurrent callers", async () => {
        mockGetDatatypesMapper.mockResolvedValue(MAPPER);
        const store = useDatatypesMapperStore();

        await Promise.all([store.createMapper(), store.createMapper()]);

        expect(mockGetDatatypesMapper).toHaveBeenCalledTimes(1);
        expect(store.datatypesMapper?.datatypes).toEqual(["tabular"]);
        expect(store.loading).toBe(false);
    });

    it("rejects every concurrent caller when the load fails", async () => {
        mockGetDatatypesMapper.mockRejectedValue(new Error("load failed"));
        const store = useDatatypesMapperStore();

        const results = await Promise.allSettled([store.createMapper(), store.createMapper()]);

        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(mockGetDatatypesMapper).toHaveBeenCalledTimes(1);
        expect(store.datatypesMapper).toBeNull();
        expect(store.loading).toBe(false);
    });

    it("keeps the shared load out of the store state", async () => {
        mockGetDatatypesMapper.mockResolvedValue(MAPPER);
        const store = useDatatypesMapperStore();

        const load = store.createMapper();

        expect(Object.keys(store.$state).sort()).toEqual(["datatypesMapper", "loading"]);
        await load;
    });

    it("retries after a failed load", async () => {
        mockGetDatatypesMapper.mockRejectedValueOnce(new Error("load failed")).mockResolvedValueOnce(MAPPER);
        const store = useDatatypesMapperStore();

        await expect(store.createMapper()).rejects.toThrow("load failed");
        await store.createMapper();

        expect(mockGetDatatypesMapper).toHaveBeenCalledTimes(2);
        expect(store.datatypesMapper?.datatypes).toEqual(["tabular"]);
    });
});
