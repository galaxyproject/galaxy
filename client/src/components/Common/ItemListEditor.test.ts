import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import ItemListEditor from "./ItemListEditor.vue";

describe("ItemListEditor", () => {
    it("renders the description through v-sanitize-html while the form is open", async () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const description = "Acceptable format: <ul><li>one</li></ul>";
        const wrapper = mount(ItemListEditor as object, {
            global: getLocalVue(),
            props: { itemName: "DOI", description },
        });

        expect(wrapper.find(".sanitized").exists()).toBe(false);
        await wrapper.find("a[href='#']").trigger("click");

        expect(sanitizeHtml).toHaveBeenCalledWith(description, "default");
        expect(wrapper.find(".sanitized li").text()).toBe("one");
    });

    it("adds the item typed into the GFormInput", async () => {
        const wrapper = mount(ItemListEditor as object, {
            global: getLocalVue(),
            props: { itemName: "DOI", items: [] },
        });

        await wrapper.find("a[href='#']").trigger("click");
        const input = wrapper.get("input");
        expect(input.classes()).toContain("g-form-input");
        await input.setValue("10.1000/xyz");
        await wrapper
            .findAll("button")
            .find((button) => button.text() === "Save")!
            .trigger("click");

        expect(wrapper.emitted("onItems")?.at(-1)).toEqual([["10.1000/xyz"]]);
    });

    it("marks the GFormInput invalid when an empty item is saved and clears it on focus", async () => {
        const wrapper = mount(ItemListEditor as object, {
            global: getLocalVue(),
            props: { itemName: "DOI", items: [] },
        });

        await wrapper.find("a[href='#']").trigger("click");
        await wrapper
            .findAll("button")
            .find((button) => button.text() === "Save")!
            .trigger("click");

        expect(wrapper.get("input").attributes("aria-invalid")).toBe("true");
        expect(wrapper.find(".error").text()).toBe("Please provide a value");

        await wrapper.get("input").trigger("focus");
        expect(wrapper.get("input").attributes("aria-invalid")).toBeUndefined();
        expect(wrapper.find(".error").exists()).toBe(false);
    });
});
