import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";

import DatasetAsImage from "./DatasetAsImage.vue";

vi.mock("@/composables/datasetPathDestination", () => ({
    useDatasetPathDestination: () => ({
        datasetPathDestination: computed(() => async () => ({ fileLink: "/dataset/display?filename=image.svg" })),
    }),
}));

const DATASET_URL = "/dataset/display?dataset_id=dataset-id&as_image=true";

describe("DatasetAsImage", () => {
    const fetchMock = vi.fn();
    let wrapper: ReturnType<typeof mount>;

    beforeEach(() => {
        vi.stubGlobal("fetch", fetchMock);
    });

    afterEach(() => {
        wrapper?.destroy();
        vi.unstubAllGlobals();
        fetchMock.mockReset();
    });

    async function render(type: string, props = {}) {
        fetchMock.mockResolvedValue(new Response("image", { headers: { "Content-Type": type } }));
        wrapper = mount(DatasetAsImage as object, {
            localVue: getLocalVue(),
            propsData: { historyDatasetId: "dataset-id", ...props },
        });
        await flushPromises();
    }

    it.each(["image/png", "image/svg+xml"])("requests and renders %s in image mode", async (type) => {
        await render(type);
        expect(fetchMock).toHaveBeenCalledWith(DATASET_URL);
        expect(wrapper.find("img").attributes("src")).toBe(DATASET_URL);
        expect(wrapper.find("svg").exists()).toBe(false);
        expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("requests extra files in image mode", async () => {
        await render("image/svg+xml", { path: "image.svg" });
        const url = "/dataset/display?filename=image.svg&as_image=true";
        expect(fetchMock).toHaveBeenCalledWith(url);
        expect(wrapper.find("img").attributes("src")).toBe(url);
    });

    it("rejects non-image responses", async () => {
        await render("text/plain");
        expect(wrapper.text()).toContain("This dataset does not appear to be an image");
        expect(wrapper.find("img").exists()).toBe(false);
    });

    it("sizes viewBox-only SVGs and preserves the size toggle", async () => {
        await render("image/svg+xml", { allowSizeToggle: true });
        const image = wrapper.find("img");
        Object.defineProperties(image.element, {
            naturalWidth: { value: 240 },
            naturalHeight: { value: 150 },
        });
        await image.trigger("load");
        expect(image.attributes("width")).toBe("240");
        expect(image.attributes("height")).toBe("150");
        expect(image.classes()).toContain("img-fluid");
        await wrapper.find(".image-wrapper").trigger("click");
        expect(image.classes()).not.toContain("img-fluid");
        expect(image.attributes("width")).toBe("240");
        expect(image.attributes("height")).toBe("150");
        await wrapper.setProps({ historyDatasetId: "another-dataset" });
        await flushPromises();
        expect(wrapper.find("img").attributes("width")).toBeUndefined();
        expect(wrapper.find("img").attributes("height")).toBeUndefined();
    });
});
