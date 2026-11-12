import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FieldFilter } from "./configs/types";
import type { ColumnFilterChip } from "./useColumnFilters";

import GridColumnFilterChips from "./GridColumnFilterChips.vue";

const WORKFLOWS: FieldFilter = { key: "workflow_id", plural: "workflows", search: async () => [] };

const CHIPS: ColumnFilterChip[] = ["one", "two", "three"].map((name) => ({
    title: "Workflow",
    filter: WORKFLOWS,
    option: { id: `id-${name}`, name },
}));

const CHIP = "[data-description='grid active column filter workflow_id']";
const MENU = "[data-description='grid hidden column filters']";
const MENU_ITEM = "[data-description='grid hidden column filter workflow_id']";
const CLEAR = "[data-description='grid clear column filters']";

function mountTarget(props: { chips: ColumnFilterChip[]; inline?: boolean }) {
    return mount(GridColumnFilterChips as object, { props, global: getLocalVue() });
}

/** Lay the chip line out as 100px per chip in a 250px line, which jsdom can't measure */
function stubLineWidths() {
    const isLine = (element: Element) => element.classList.contains("column-filter-chips-line");
    // jsdom defines `clientWidth` on HTMLElement and `scrollWidth` on Element
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: Element) {
        return isLine(this) ? 250 : 0;
    });
    vi.spyOn(Element.prototype, "scrollWidth", "get").mockImplementation(function (this: Element) {
        return isLine(this) ? this.querySelectorAll(".column-filter-chip").length * 100 : 0;
    });
}

afterEach(() => {
    vi.restoreAllMocks();
});

describe("GridColumnFilterChips", () => {
    it("shows every chip, without a menu or Clear, when not inline", async () => {
        const wrapper = mountTarget({ chips: CHIPS });
        await flushPromises();

        expect(wrapper.findAll(CHIP).map((chip) => chip.text())).toEqual([
            "Workflow: one",
            "Workflow: two",
            "Workflow: three",
        ]);
        expect(wrapper.find(MENU).exists()).toBe(false);
        expect(wrapper.find(CLEAR).exists()).toBe(false);
    });

    it("emits the removed chip's filter and option", async () => {
        const wrapper = mountTarget({ chips: CHIPS, inline: true });
        await flushPromises();
        await wrapper.findAll(CHIP)[1]!.trigger("click");
        expect(wrapper.emitted("remove")).toEqual([[WORKFLOWS, CHIPS[1]!.option]]);
    });

    it("inline, keeps the chips that fit on the line and moves the rest to a menu", async () => {
        stubLineWidths();
        const wrapper = mountTarget({ chips: CHIPS, inline: true });
        await flushPromises();

        expect(wrapper.findAll(CHIP).map((chip) => chip.text())).toEqual(["Workflow: one", "Workflow: two"]);
        const menu = wrapper.find(MENU);
        expect(menu.text()).toContain("+1 more");

        await menu.find("button").trigger("click");
        await flushPromises();
        const hidden = wrapper.find(MENU_ITEM);
        expect(hidden.text()).toContain("Workflow: three");
        await hidden.trigger("click");
        expect(wrapper.emitted("remove")).toEqual([[WORKFLOWS, CHIPS[2]!.option]]);
    });

    it("inline, emits clear from the Clear link", async () => {
        const wrapper = mountTarget({ chips: CHIPS, inline: true });
        await flushPromises();
        await wrapper.find(CLEAR).trigger("click");
        expect(wrapper.emitted("clear")).toHaveLength(1);
    });

    it("renders nothing without chips", () => {
        expect(mountTarget({ chips: [] }).find("[data-description='grid active column filters']").exists()).toBe(false);
    });
});
