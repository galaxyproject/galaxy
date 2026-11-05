import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { getDatatypesMapper } from "@/components/Datatypes";
import { Toast } from "@/composables/toast";

import { useExtensionFiltering } from "./useExtensionFilter";

vi.mock("@/components/Datatypes", () => ({
    getDatatypesMapper: vi.fn(),
}));

vi.mock("@/composables/toast");

describe("useExtensionFiltering", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(getDatatypesMapper).mockReset();
        vi.mocked(Toast.error).mockReset();
    });

    it("shows one error toast and filters nothing when the datatypes fail to load", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValueOnce(new Error("Datatypes unavailable"));

        const scope = effectScope();
        const filters = scope.run(() => [
            useExtensionFiltering({ extensions: ["tabular"] }),
            useExtensionFiltering({ extensions: ["tabular"] }),
        ])!;
        await flushPromises();

        expect(getDatatypesMapper).toHaveBeenCalledTimes(1);
        expect(Toast.error).toHaveBeenCalledTimes(1);
        expect(Toast.error).toHaveBeenCalledWith("Datatypes unavailable", "Unable to load datatypes");
        expect(filters[0]!.hasInvalidExtension({ extension: "txt" })).toBe(false);
        scope.stop();
    });
});
