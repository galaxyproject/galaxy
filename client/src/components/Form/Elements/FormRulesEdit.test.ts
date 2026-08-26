import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCollectionDetails } from "@/api/datasetCollections";
import type { HDCADetailed } from "@/api/index.js";

import FormRulesEdit from "./FormRulesEdit.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";
import RulesDisplay from "@/components/RulesDisplay/RulesDisplay.vue";

vi.mock("@/api/datasetCollections", () => ({
    fetchCollectionDetails: vi.fn(),
}));

const localVue = getLocalVue();

const collectionData = { id: "hdca1", collection_type: "list" } as HDCADetailed;

function mountComponent(propsData: Record<string, unknown> = {}) {
    return mount(FormRulesEdit as object, {
        localVue,
        propsData: { id: "rules-edit", ...propsData },
        stubs: {
            RuleGrid: true,
        },
    });
}

describe("FormRulesEdit", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders RulesDisplay with the provided rules", () => {
        const value = { rules: [{ type: "add_column_value", value: "x" }], mapping: [] };
        const wrapper = mountComponent({ value });
        expect(wrapper.findComponent(RulesDisplay).props("inputRules")).toEqual(value);
    });

    it("opens the modal directly when there is no target", async () => {
        const wrapper = mountComponent();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(fetchCollectionDetails).not.toHaveBeenCalled();
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(wrapper.findComponent(RuleCollectionBuilder).exists()).toBe(true);
    });

    it("fetches collection details and opens the modal when a target is set", async () => {
        const target = { id: "hdca1" };
        vi.mocked(fetchCollectionDetails).mockResolvedValue({ data: collectionData, error: undefined });

        const wrapper = mountComponent({ target });
        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(fetchCollectionDetails).toHaveBeenCalledWith({ hdca_id: "hdca1" });
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);

        const builder = wrapper.findComponent(RuleCollectionBuilder);
        expect(builder.exists()).toBe(true);
        expect(builder.props("initialElements")).toEqual(collectionData);
    });

    it("does not open the modal when the fetch fails", async () => {
        const target = { id: "hdca1" };
        vi.mocked(fetchCollectionDetails).mockResolvedValue({
            data: undefined,
            error: new Error("failed to load collection"),
        });

        const wrapper = mountComponent({ target });
        await wrapper.find("button").trigger("click");
        await flushPromises();

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(wrapper.text()).toContain("failed to load collection");
    });
});
