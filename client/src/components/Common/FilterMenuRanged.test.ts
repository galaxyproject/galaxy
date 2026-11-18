import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { equals } from "@/utils/filtering";

import FilterMenuRanged from "./FilterMenuRanged.vue";

const INDEX_FILTER = { placeholder: "index", type: Number, handler: equals("hid"), isRangeInput: true, menuItem: true };

function mountRanged(props: Record<string, unknown> = {}) {
    return mount(FilterMenuRanged, {
        props: { name: "hid", identifier: "test-list", filter: INDEX_FILTER, filters: { hid_gt: "2" }, ...props },
        global: getLocalVue(),
    });
}

function gtInput(wrapper: ReturnType<typeof mountRanged>) {
    return wrapper.get("input#test-list-advanced-filter-hid_gt");
}

function ltInput(wrapper: ReturnType<typeof mountRanged>) {
    return wrapper.get("input#test-list-advanced-filter-hid_lt");
}

describe("FilterMenuRanged", () => {
    it("renders both bounds in small GFormInput fields", () => {
        const wrapper = mountRanged();
        for (const input of [gtInput(wrapper), ltInput(wrapper)]) {
            expect(input.classes()).toEqual(expect.arrayContaining(["g-form-input", "g-small"]));
        }
        expect(gtInput(wrapper).attributes("placeholder")).toBe("greater than index");
        expect(ltInput(wrapper).attributes("placeholder")).toBe("lower than index");
        expect((gtInput(wrapper).element as HTMLInputElement).value).toBe("2");
    });

    it("emits change with the bound name and the typed value", async () => {
        const wrapper = mountRanged();
        await gtInput(wrapper).setValue("3");
        expect(wrapper.emitted("change")?.at(-1)).toEqual(["hid_gt", "3"]);
        await ltInput(wrapper).setValue("9");
        expect(wrapper.emitted("change")?.at(-1)).toEqual(["hid_lt", "9"]);
    });

    it("shows the new bounds when the parent updates the filters", async () => {
        const wrapper = mountRanged();
        await wrapper.setProps({ filters: { hid_gt: "5", hid_lt: "7" } });
        expect((gtInput(wrapper).element as HTMLInputElement).value).toBe("5");
        expect((ltInput(wrapper).element as HTMLInputElement).value).toBe("7");
    });

    it("emits on-enter and on-esc from the keyboard", async () => {
        const wrapper = mountRanged();
        await ltInput(wrapper).trigger("keyup.enter");
        await gtInput(wrapper).trigger("keyup.esc");
        expect(wrapper.emitted("on-enter")).toHaveLength(1);
        expect(wrapper.emitted("on-esc")).toHaveLength(1);
    });

    it("marks only the bound with the error invalid", () => {
        const wrapper = mountRanged({ error: { filter: "hid", index: "hid_lt", msg: "Not a number" } });
        expect(ltInput(wrapper).attributes("aria-invalid")).toBe("true");
        expect(ltInput(wrapper).attributes("data-mock-directive")).toBe("Not a number");
        expect(gtInput(wrapper).attributes("aria-invalid")).toBeUndefined();
    });
});
