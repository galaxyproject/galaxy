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
            localVue: getLocalVue(),
            propsData: { itemName: "DOI", description },
        });

        expect(wrapper.find(".sanitized").exists()).toBe(false);
        await wrapper.find("a[href='#']").trigger("click");

        expect(sanitizeHtml).toHaveBeenCalledWith(description, "default");
        expect(wrapper.find(".sanitized li").text()).toBe("one");
    });
});
