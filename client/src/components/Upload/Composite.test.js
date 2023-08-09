import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import mountTarget from "./Composite.vue";

const localVue = getLocalVue();

function getWrapper() {
    return mount(mountTarget, {
        propsData: {
            defaultDbKey: "?",
            effectiveExtensions: [{ id: "affybatch", composite_files: [] }],
            fileSourcesConfigured: true,
            ftpUploadSite: null,
            historyId: "historyId",
            listDbKeys: [],
        },
        localVue,
    });
}

describe("Composite", () => {
    it("rendering", async () => {
        const wrapper = getWrapper();
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.vm.showHelper).toBe(true);
        expect(wrapper.vm.readyStart).toBe(false);
        const extensions = wrapper.vm.listExtensions;
        expect(extensions.length).toBe(2);
        expect(extensions[0].id).toBe(null);
        expect(extensions[0].text).toBe("Select");
        expect(extensions[1].id).toBe("affybatch");
    });
});
