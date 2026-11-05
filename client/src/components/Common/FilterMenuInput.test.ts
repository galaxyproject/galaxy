import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { contains } from "@/utils/filtering";

import FilterMenuInput from "./FilterMenuInput.vue";

const NAME_FILTER = { placeholder: "name", type: String, handler: contains("name"), menuItem: true };

function mountInput(props: Record<string, unknown> = {}) {
    return mount(FilterMenuInput, {
        props: { name: "name", identifier: "test-list", filter: NAME_FILTER, filters: { name: "old" }, ...props },
        global: getLocalVue(),
    });
}

describe("FilterMenuInput", () => {
    it("renders the filter value in a small GFormInput", () => {
        const input = mountInput().get("input#test-list-advanced-filter-name");
        expect(input.classes()).toEqual(expect.arrayContaining(["g-form-input", "g-small", "mw-100"]));
        expect(input.attributes("placeholder")).toBe("any name");
        expect((input.element as HTMLInputElement).value).toBe("old");
    });

    it("emits change with the filter name and the typed value", async () => {
        const wrapper = mountInput();
        await wrapper.get("input").setValue("new");
        expect(wrapper.emitted("change")?.at(-1)).toEqual(["name", "new"]);
    });

    it("shows the new value when the parent updates the filters", async () => {
        const wrapper = mountInput();
        await wrapper.setProps({ filters: { name: "from-parent" } });
        expect((wrapper.get("input").element as HTMLInputElement).value).toBe("from-parent");
    });

    it("emits on-enter and on-esc from the keyboard", async () => {
        const wrapper = mountInput();
        await wrapper.get("input").trigger("keyup.enter");
        await wrapper.get("input").trigger("keyup.esc");
        expect(wrapper.emitted("on-enter")).toHaveLength(1);
        expect(wrapper.emitted("on-esc")).toHaveLength(1);
    });

    it("marks the field invalid when the filter has an error", () => {
        const input = mountInput({ error: "Invalid name" }).get("input");
        expect(input.attributes("aria-invalid")).toBe("true");
        expect(input.attributes("data-mock-directive")).toBe("Invalid name");
    });

    it("links the field to its datalist and disables it", () => {
        const input = mountInput({
            filter: { ...NAME_FILTER, datalist: ["a", "b"] },
            disabled: true,
        }).get("input");
        expect(input.attributes("list")).toBe("test-list-name-selectList");
        expect(input.attributes("disabled")).toBeDefined();
    });
});
