import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CuratedCollectionChips from "./CuratedCollectionChips.vue";

const localVue = getLocalVue();

const COLLECTIONS = [
    { name: "Microbiome", count: 21 },
    { name: "Epigenetics", count: 12 },
    { name: "Transcriptomics", count: 11 },
    { name: "Imaging", count: 4 },
    { name: "Virology", count: 3 },
];

/** Collections that land on the first row in the faked layout; the rest wrap below it. */
let firstRow: string[] = [];

function fakeOffset(element: HTMLElement, property: "offsetTop" | "offsetHeight" | "offsetWidth") {
    if (property === "offsetHeight") {
        return 24;
    }
    if (property === "offsetWidth") {
        return 60;
    }
    const collection = element.dataset.collection;
    return collection === undefined || firstRow.includes(collection) ? 0 : 30;
}

async function mountChips(active?: string) {
    const wrapper = mount(CuratedCollectionChips as object, {
        localVue,
        propsData: { collections: COLLECTIONS, active },
    });
    await flushPromises();
    return wrapper;
}

function hiddenChips(wrapper: Awaited<ReturnType<typeof mountChips>>) {
    return wrapper
        .findAll(".curated-workflow-collection-hidden")
        .wrappers.map((chip) => chip.attributes("data-collection"));
}

describe("CuratedCollectionChips", () => {
    beforeEach(() => {
        firstRow = ["Microbiome", "Epigenetics"];
        for (const property of ["offsetTop", "offsetHeight", "offsetWidth"] as const) {
            vi.spyOn(HTMLElement.prototype, property, "get").mockImplementation(function (this: HTMLElement) {
                return fakeOffset(this, property);
            });
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("keeps to one row and offers the rest behind a +N more button", async () => {
        const wrapper = await mountChips();

        expect(hiddenChips(wrapper)).toEqual(["Transcriptomics", "Imaging", "Virology"]);
        expect(wrapper.find(".curated-workflow-collection-hidden").attributes("tabindex")).toBe("-1");
        const more = wrapper.find(".curated-workflow-collections-more");
        expect(more.text()).toBe("+3 more");
        expect(more.classes()).not.toContain("g-pressed");
    });

    it("shows every chip once expanded, and folds them away again", async () => {
        const wrapper = await mountChips();

        await wrapper.find(".curated-workflow-collections-more").trigger("click");
        await flushPromises();

        expect(hiddenChips(wrapper)).toEqual([]);
        expect(wrapper.find(".curated-workflow-collections-more").exists()).toBe(false);

        await wrapper.find(".curated-workflow-collections-less").trigger("click");
        await flushPromises();

        expect(hiddenChips(wrapper)).toEqual(["Transcriptomics", "Imaging", "Virology"]);
    });

    it("needs no button when everything fits", async () => {
        firstRow = COLLECTIONS.map((collection) => collection.name);
        const wrapper = await mountChips();

        expect(hiddenChips(wrapper)).toEqual([]);
        expect(wrapper.find(".curated-workflow-collections-more").exists()).toBe(false);
        expect(wrapper.find(".curated-workflow-collections-less").exists()).toBe(false);
    });

    it("marks +N more as selected when the active collection is folded away", async () => {
        const wrapper = await mountChips("imaging");

        expect(wrapper.find(".curated-workflow-collections-more").classes()).toContain("g-pressed");
    });

    it("asks to toggle a collection when its chip is clicked", async () => {
        const wrapper = await mountChips();

        await wrapper.find('[data-collection="Epigenetics"]').trigger("click");

        expect(wrapper.emitted("toggle")).toEqual([["Epigenetics"]]);
    });
});
