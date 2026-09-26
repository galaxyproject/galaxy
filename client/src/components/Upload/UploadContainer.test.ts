import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, expect, it, vi } from "vitest";

import { getDatatypesMapper } from "@/components/Datatypes";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { getUploadDatatypes, getUploadDbKeys } from "@/components/Upload/utils";

import UploadContainer from "./UploadContainer.vue";

vi.mock("@/components/Datatypes", () => ({ getDatatypesMapper: vi.fn() }));
vi.mock("@/components/Upload/utils", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    getUploadDatatypes: vi.fn(),
    getUploadDbKeys: vi.fn(),
}));
vi.mock("./CompositeBox.vue", () => ({ default: {} }));
vi.mock("./DefaultBox.vue", () => ({ default: {} }));
vi.mock("./RulesInput.vue", () => ({ default: {} }));

beforeEach(() => {
    vi.mocked(getUploadDatatypes).mockResolvedValue([]);
    vi.mocked(getUploadDbKeys).mockResolvedValue([]);
    vi.mocked(getDatatypesMapper).mockResolvedValue(
        new DatatypesMapperModel({
            datatypes: [],
            datatypes_mapping: { ext_to_class_name: {}, class_to_classes: {} },
        }),
    );
});

it.each(["genomes", "formats", "mapper"])(
    "displays a failed %s request without an unhandled rejection",
    async (resource) => {
        const request =
            resource === "genomes" ? getUploadDbKeys : resource === "formats" ? getUploadDatatypes : getDatatypesMapper;
        vi.mocked(request).mockRejectedValueOnce(new TypeError("Failed to fetch"));
        const wrapper = shallowMount(UploadContainer, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { currentHistoryId: "history-id", formats: ["txt"] },
        });
        await flushPromises();
        expect(wrapper.text()).toContain("Unable to load upload options: Failed to fetch");
        wrapper.destroy();
    },
);
