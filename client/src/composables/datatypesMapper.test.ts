import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDatatypesMapper } from "@/components/Datatypes";
import { Toast } from "@/composables/toast";

import { useDatatypesMapper } from "./datatypesMapper";

vi.mock("@/components/Datatypes", () => ({
    getDatatypesMapper: vi.fn(),
}));

vi.mock("@/composables/toast");

describe("useDatatypesMapper", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(getDatatypesMapper).mockReset();
        vi.mocked(Toast.error).mockReset();
    });

    it("stops loading and shows an error toast when the datatypes fail to load", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValue(new Error("Datatypes unavailable"));

        const { datatypesMapper, datatypesMapperLoading } = useDatatypesMapper();
        await flushPromises();

        expect(datatypesMapperLoading.value).toBe(false);
        expect(datatypesMapper.value).toBeNull();
        expect(Toast.error).toHaveBeenCalledWith("Datatypes unavailable", "Unable to load datatypes");
    });

    it("shows one error toast per failed load, not one per instance", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValueOnce(new Error("Datatypes unavailable"));

        useDatatypesMapper();
        useDatatypesMapper();
        await flushPromises();

        expect(getDatatypesMapper).toHaveBeenCalledTimes(1);
        expect(Toast.error).toHaveBeenCalledTimes(1);

        vi.mocked(getDatatypesMapper).mockRejectedValueOnce(new Error("Datatypes still unavailable"));

        useDatatypesMapper();
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledTimes(2);
        expect(Toast.error).toHaveBeenLastCalledWith("Datatypes still unavailable", "Unable to load datatypes");
    });
});
