import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SlugInput from "./SlugInput.vue";

function mountSlugInput() {
    return mount(SlugInput, { props: { slug: "my-page" }, global: getLocalVue() });
}

describe("SlugInput", () => {
    it("emits the formatted slug when the input changes", async () => {
        const wrapper = mountSlugInput();
        const input = wrapper.get("input");
        expect(input.classes()).toContain("g-form-input");
        expect(input.element.value).toBe("my-page");

        await input.setValue("My New/Page?");
        await input.trigger("change");
        expect(wrapper.emitted("change")?.at(-1)).toEqual(["my-newpage"]);
    });

    it("emits the initial slug when editing is cancelled with Escape", async () => {
        const wrapper = mountSlugInput();
        await wrapper.get("input").trigger("keydown", { key: "Escape" });
        expect(wrapper.emitted("change")).toEqual([["my-page"]]);
    });
});
