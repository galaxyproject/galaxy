import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { getUploadDatatypes, getUploadDbKeys } from "@/components/Upload/utils";
import { Toast } from "@/composables/toast";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import { useUploadConfigurations } from "./uploadConfigurations";

vi.mock("@/composables/toast");
vi.mock("@/components/Upload/utils", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    getUploadDatatypes: vi.fn(),
    getUploadDbKeys: vi.fn(),
}));
vi.mock("./config", () => ({
    useConfig: () => ({ config: ref({ default_genome: "?" }), isConfigLoaded: ref(true) }),
}));

const localVue = getLocalVue();

describe("upload configuration failures", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
        vi.mocked(getUploadDatatypes).mockResolvedValue([]);
        vi.mocked(getUploadDbKeys).mockResolvedValue([]);
        const store = useDatatypesMapperStore();
        vi.spyOn(store, "createMapper").mockImplementation(async () => {
            store.datatypesMapper = new DatatypesMapperModel({
                datatypes: [],
                datatypes_mapping: { ext_to_class_name: {}, class_to_classes: {} },
            });
        });
    });

    it.each(["genomes", "formats", "datatypes", "none"])(
        "handles upload initialization with failure: %s",
        async (resource) => {
            const error = new TypeError("Failed to fetch");
            if (resource === "genomes") {
                vi.mocked(getUploadDbKeys).mockRejectedValue(error);
            } else if (resource === "formats") {
                vi.mocked(getUploadDatatypes).mockRejectedValue(error);
            } else if (resource === "datatypes") {
                vi.mocked(useDatatypesMapperStore().createMapper).mockRejectedValue(error);
            }
            let configurations: ReturnType<typeof useUploadConfigurations>;
            const wrapper = mount(
                defineComponent({
                    setup() {
                        configurations = useUploadConfigurations(undefined);
                        return {};
                    },
                    template: "<div />",
                }),
                { localVue },
            );
            await flushPromises();

            if (resource === "none") {
                expect(Toast.error).not.toHaveBeenCalled();
                expect(configurations!.ready.value).toBe(true);
            } else {
                expect(Toast.error).toHaveBeenCalledWith("Failed to fetch", `Unable to load upload ${resource}`);
                expect(configurations!.ready.value).toBe(false);
            }
            wrapper.destroy();
        },
    );
});
