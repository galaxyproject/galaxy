import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import DatasetDownload from "./DatasetDownload";

const localVue = getLocalVue();

const items = [
    { id: "item_id", extension: "ext", meta_files: [{ file_type: "a" }, { file_type: "b" }] },
    { id: "item_id", extension: "ext", meta_files: [] },
];

describe("DatasetDownload", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(DatasetDownload, {
            propsData: {
                item: items[0],
            },
            localVue,
        });
    });

    it("checks basics", async () => {
        const dropdownItems = wrapper.findAll(".dropdown-item");
        expect(dropdownItems.length).toBe(3);
        expect(dropdownItems.at(0).text()).toBe("Download Dataset");
        expect(dropdownItems.at(1).text()).toBe("Download a");
        expect(dropdownItems.at(2).text()).toBe("Download b");
        for (let i = 0; i < dropdownItems.length; i++) {
            await dropdownItems.at(i).trigger("click");
        }
        await wrapper.setProps({ item: items[1] });
        const foundItems = wrapper.find(".dropdown-item").exists();
        expect(foundItems).toBe(false);
        await wrapper.trigger("click");
        const emitted = wrapper.emitted()["on-download"];
        expect(emitted[0][0]).toBe(`/api/datasets/item_id/display?to_ext=ext`);
        expect(emitted[1][0]).toBe(`/api/datasets/item_id/metadata_file?metadata_file=a`);
        expect(emitted[2][0]).toBe(`/api/datasets/item_id/metadata_file?metadata_file=b`);
        expect(emitted[3][0]).toBe(`/api/datasets/item_id/display?to_ext=ext`);
    });
});
