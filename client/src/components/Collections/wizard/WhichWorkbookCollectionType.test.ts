import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import navigation from "@/utils/navigation/navigation.yml";

import WhichWorkbookCollectionType from "./WhichWorkbookCollectionType.vue";

const localVue = getLocalVue();

function mountWithValue(value = "list") {
    return mount(WhichWorkbookCollectionType as object, { propsData: { value }, localVue });
}

function typeCards(wrapper: ReturnType<typeof mountWithValue>) {
    return wrapper.findAll("[data-collection-type], [data-which-builder]");
}

function cardFor(wrapper: ReturnType<typeof mountWithValue>, collectionType: string) {
    return wrapper.find(`[data-collection-type='${collectionType}'], [data-which-builder='${collectionType}']`);
}

describe("WhichWorkbookCollectionType", () => {
    it("offers the five list types", () => {
        const wrapper = mountWithValue();
        expect(typeCards(wrapper).map((card) => card.find(".card-title").text())).toEqual([
            "Flat List",
            "List of Paired Datasets",
            "Mixed List of Paired and Unpaired Datasets",
            "Nested List of Datasets",
            "Nested List of Paired Datasets",
        ]);
    });

    it("keeps the advanced list types on a row of their own", () => {
        const wrapper = mountWithValue();
        const rows = wrapper.findAll(".collection-type-card-grid");
        expect(rows.map((row) => row.findAll("[data-collection-type]").length)).toEqual([2, 3]);
    });

    it.each(["list", "list:paired", "list:paired_or_unpaired", "list:list", "list:list:paired"])(
        "picks %s",
        async (collectionType) => {
            const wrapper = mountWithValue();
            await cardFor(wrapper, collectionType).trigger("click");
            expect(wrapper.emitted("onChange")).toEqual([[collectionType]]);
        },
    );

    it.each(["list", "list:paired", "list:paired_or_unpaired", "list:list", "list:list:paired"])(
        "lets browser tests select the %s workbook template",
        async (collectionType) => {
            const wrapper = mountWithValue();
            const selector = navigation.file_set_wizard.selectors.which_builder.replace("${builder}", collectionType);
            await wrapper.find(selector).trigger("click");
            expect(wrapper.emitted("onChange")).toEqual([[collectionType]]);
        },
    );

    it("marks the current collection type", () => {
        const wrapper = mountWithValue("list:paired");
        expect(cardFor(wrapper, "list:paired").classes()).toContain("border-primary");
        expect(cardFor(wrapper, "list").classes()).not.toContain("border-primary");
    });
});
