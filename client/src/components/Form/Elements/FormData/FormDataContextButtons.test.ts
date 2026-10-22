import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormDataContextButtons from "./FormDataContextButtons.vue";

const localVue = getLocalVue();

function mountForCollectionTypes(collectionTypes: string[]) {
    return mount(FormDataContextButtons as object, {
        props: { collectionTypes, currentSource: "hdca", workflowTab: "", showViewCreateOptions: true },
        global: localVue,
    });
}

function createTitle(wrapper: ReturnType<typeof mountForCollectionTypes>) {
    const create = wrapper.find("[data-description='upload']");
    return create.attributes("title") ?? create.attributes("data-original-title");
}

describe("FormDataContextButtons", () => {
    it("names the collection a single builder creates", () => {
        expect(createTitle(mountForCollectionTypes(["list:paired"]))).toBe("Create a new list of pairs");
    });

    it("names a sample sheet the builder creates", () => {
        expect(createTitle(mountForCollectionTypes(["sample_sheet:paired"]))).toBe(
            "Create a new sample sheet of pairs",
        );
    });

    it("names each builder offered", () => {
        const wrapper = mountForCollectionTypes(["list:paired_or_unpaired"]);
        expect(createTitle(wrapper)).toBe("Create a new list");
        expect(wrapper.text()).toContain("List of pairs");
        expect(wrapper.text()).toContain("Mixed list of paired and unpaired");
    });
});
