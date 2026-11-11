import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { BasedOnWork } from "@/api/workflows";

import BasedOnEditor from "./BasedOnEditor.vue";
import BasedOnViewer from "./BasedOnViewer.vue";

const localVue = getLocalVue();

const NF_CORE_DEMO: BasedOnWork = {
    class: "SoftwareSourceCode",
    name: "nf-core/demo",
    url: "https://github.com/nf-core/demo",
    version: "1.0.2",
    identifier: "doi:10.5281/zenodo.12192442",
    description: "Not editable in the form.",
    creator: [{ class: "Person", name: "Christopher Hakkaart" }],
};

function mountEditor(works: BasedOnWork[] = []) {
    return mount(BasedOnEditor as object, { props: { works }, global: localVue });
}

describe("BasedOnEditor", () => {
    it("adds an upstream work entered in the form", async () => {
        const wrapper = mountEditor();

        await wrapper.find("#based-on-add").trigger("click");
        await wrapper.find("#based-on-name").setValue("nf-core/rnaseq");
        await wrapper.find("#based-on-version").setValue("3.14.0");
        await wrapper.find("#based-on-save").trigger("click");

        expect(wrapper.emitted("onBasedOn")).toEqual([
            [[{ class: "SoftwareSourceCode", name: "nf-core/rnaseq", version: "3.14.0" }]],
        ]);
    });

    it("requires a name before saving", async () => {
        const wrapper = mountEditor();

        await wrapper.find("#based-on-add").trigger("click");
        await wrapper.find("#based-on-save").trigger("click");

        expect(wrapper.emitted("onBasedOn")).toBeUndefined();
        expect(wrapper.find(".based-on-form").text()).toContain("Please provide a name");
    });

    it("keeps attributes the form does not edit and drops cleared ones", async () => {
        const wrapper = mountEditor([NF_CORE_DEMO]);

        await wrapper.find("[data-title='Edit Upstream Work']").trigger("click");
        await wrapper.find("#based-on-version").setValue("");
        await wrapper.find("#based-on-save").trigger("click");

        const { version: _version, ...withoutVersion } = NF_CORE_DEMO;
        expect(wrapper.emitted("onBasedOn")).toEqual([[[withoutVersion]]]);
    });

    it("removes an upstream work", async () => {
        const wrapper = mountEditor([NF_CORE_DEMO]);

        await wrapper.find("[data-title='Remove Upstream Work']").trigger("click");

        expect(wrapper.emitted("onBasedOn")).toEqual([[[]]]);
    });
});

describe("BasedOnViewer", () => {
    it("links the work, its DOI and credits its creators", () => {
        const wrapper = mount(BasedOnViewer as object, { props: { work: NF_CORE_DEMO }, global: localVue });

        expect(wrapper.find("[itemprop='isBasedOn']").attributes("itemtype")).toBe(
            "https://schema.org/SoftwareSourceCode",
        );
        const links = wrapper.findAll("a").map((link) => link.attributes("href"));
        expect(links).toContain("https://github.com/nf-core/demo");
        expect(links).toContain("https://doi.org/10.5281/zenodo.12192442");
        expect(wrapper.find(".based-on-creators").text()).toContain("Christopher Hakkaart");
    });
});
