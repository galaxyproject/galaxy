import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import DatasetDownload from "./DatasetDownload.vue";

enableAutoUnmount(afterEach);

const datasetWithMetadata = {
    id: "item_id",
    extension: "ext",
    file_size: 1024,
    meta_files: [{ file_type: "a" }, { file_type: "b" }],
};
const datasetWithoutMetadata = { id: "item_id", extension: "ext", file_size: 0, meta_files: [] };

function mountDownload(item = datasetWithMetadata): VueWrapper {
    return mount(DatasetDownload as object, {
        props: { item },
        global: getLocalVue(),
    });
}

describe("DatasetDownload", () => {
    it("offers the dataset and each metadata file as separate downloads", () => {
        const wrapper = mountDownload();

        expect(wrapper.findAll(".dropdown-item").map((item) => item.text())).toEqual([
            "Download Dataset",
            "Download a",
            "Download b",
        ]);
    });

    it.each([
        { label: "Download Dataset", url: "/api/datasets/item_id/download?to_ext=ext" },
        { label: "Download a", url: "/api/datasets/item_id/metadata_file?metadata_file=a" },
        { label: "Download b", url: "/api/datasets/item_id/metadata_file?metadata_file=b" },
    ])("emits the download URL for $label", async ({ label, url }) => {
        const wrapper = mountDownload();
        const link = wrapper.findAll(".dropdown-item").find((item) => item.text() === label);
        expect(link).toBeDefined();

        await link!.trigger("click");

        expect(wrapper.emitted("on-download")).toEqual([[url]]);
    });

    it("replaces the metadata menu with a direct download when the item loses its metadata files", async () => {
        const wrapper = mountDownload();
        for (const link of wrapper.findAll(".dropdown-item")) {
            await link.trigger("click");
        }

        await wrapper.setProps({ item: datasetWithoutMetadata });

        expect(wrapper.find(".dropdown-item").exists()).toBe(false);
        expect(wrapper.attributes("href")).toBe("/api/datasets/item_id/download?to_ext=ext");
        await wrapper.trigger("click");
        expect(wrapper.emitted("on-download")).toEqual([
            ["/api/datasets/item_id/download?to_ext=ext"],
            ["/api/datasets/item_id/metadata_file?metadata_file=a"],
            ["/api/datasets/item_id/metadata_file?metadata_file=b"],
            ["/api/datasets/item_id/download?to_ext=ext"],
        ]);
    });
});
