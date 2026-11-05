import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import InstallVisualizationModal from "./InstallVisualizationModal.vue";

const localVue = getLocalVue();

const ModalStub = {
    name: "GModal",
    props: ["okDisabled"],
    template: "<div><slot /></div>",
};

async function openFor(name: string, installedIds: string[] = []) {
    const wrapper = mount(InstallVisualizationModal, {
        localVue,
        stubs: { GModal: ModalStub },
        propsData: {
            show: false,
            packageData: { name, version: "1.0.0", description: "" },
            installedVisualizations: installedIds.map((id) => ({
                id,
                package: `@galaxyproject/${id}`,
                version: "1.0.0",
                enabled: true,
                installed: true,
            })),
        },
    });
    await wrapper.setProps({ show: true });
    return wrapper;
}

describe("InstallVisualizationModal", () => {
    it("installs under the package's unscoped name, hyphens included", async () => {
        // the backend requires static/<id>.xml, and packages name that file after themselves
        const wrapper = await openFor("@galaxyproject/foo-bar");
        expect(wrapper.find("code").text()).toBe("foo-bar");
        expect(wrapper.find("input").exists()).toBe(false);
        expect(wrapper.findComponent(ModalStub).props("okDisabled")).toBe(false);
    });

    it("refuses a package whose name can't be an id", async () => {
        const wrapper = await openFor("@galaxyproject/foo.bar");
        expect(wrapper.text()).toContain("can't be a visualization ID");
        expect(wrapper.findComponent(ModalStub).props("okDisabled")).toBe(true);
    });

    it("blocks installing over an installed id and points at Update", async () => {
        const wrapper = await openFor("@galaxyproject/foo", ["foo"]);
        expect(wrapper.text()).toContain("Update");
        expect(wrapper.text()).not.toContain("will replace it");
        expect(wrapper.findComponent(ModalStub).props("okDisabled")).toBe(true);
    });
});
