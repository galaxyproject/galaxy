import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WhichBuilder from "./WhichBuilder.vue";

const localVue = getLocalVue();

function mountWhichBuilder(initialAdvanced = false, value = "list") {
    return mount(WhichBuilder as object, { propsData: { value, initialAdvanced }, localVue });
}

function builderCards(wrapper: ReturnType<typeof mountWhichBuilder>) {
    return wrapper.findAll("[data-collection-type], [data-which-builder]");
}

function cardFor(wrapper: ReturnType<typeof mountWhichBuilder>, builder: string) {
    return wrapper.find(`[data-collection-type='${builder}'], [data-which-builder='${builder}']`);
}

describe("WhichBuilder", () => {
    it("offers the flat list, paired list and rule builder", () => {
        const wrapper = mountWhichBuilder();
        expect(builderCards(wrapper).map((card) => card.find(".card-title").text())).toEqual([
            "Flat List",
            "List of Paired Datasets",
            "Rule Builder",
        ]);
    });

    it("shows the advanced builders once asked", async () => {
        const wrapper = mountWhichBuilder();
        await wrapper.find("button").trigger("click");
        expect(builderCards(wrapper).map((card) => card.find(".card-title").text())).toEqual([
            "Flat List",
            "List of Paired Datasets",
            "Rule Builder",
            "Mixed List of Paired and Unpaired Datasets",
            "Nested List of Datasets",
            "Nested List of Paired Datasets",
        ]);
    });

    it("starts with the advanced builders shown when asked to", () => {
        const wrapper = mountWhichBuilder(true);
        expect(builderCards(wrapper)).toHaveLength(6);
        expect(wrapper.find("button").exists()).toBe(false);
    });

    it.each(["list", "list:paired", "rules", "list:paired_or_unpaired", "list:list", "list:list:paired"])(
        "picks %s",
        async (builder) => {
            const wrapper = mountWhichBuilder(true);
            await cardFor(wrapper, builder).trigger("click");
            expect(wrapper.emitted("onChange")).toEqual([[builder]]);
        },
    );

    it("marks the current builder", () => {
        const wrapper = mountWhichBuilder(true, "list:list");
        expect(cardFor(wrapper, "list:list").classes()).toContain("border-primary");
        expect(cardFor(wrapper, "list").classes()).not.toContain("border-primary");
    });
});
