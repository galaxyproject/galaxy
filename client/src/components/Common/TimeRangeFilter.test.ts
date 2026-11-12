import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { TimeRange } from "./timeRanges";

import TimeRangeFilter from "./TimeRangeFilter.vue";

const RANGES: TimeRange[] = [
    { key: "24h", label: "Last 24 hours", durationMs: 1 },
    { key: "7d", label: "Last week", durationMs: 7 },
];

function mountTarget(activeRange?: string) {
    return mount(TimeRangeFilter as object, {
        props: { ranges: RANGES, noun: "items", activeRange },
        global: getLocalVue(),
    });
}

describe("TimeRangeFilter", () => {
    it("offers Anytime and the given ranges", () => {
        const wrapper = mountTarget();
        expect(wrapper.findAll("option").map((option) => option.text())).toEqual([
            "Anytime",
            "Last 24 hours",
            "Last week",
        ]);
        expect(wrapper.find("select").attributes("aria-label")).toBe("Filter items by time range");
    });

    it("emits the picked range, or undefined for Anytime", async () => {
        const wrapper = mountTarget("24h");
        const select = wrapper.find("select");
        await select.setValue("7d");
        // "Anytime" has no value, so pick it by position
        (select.element as HTMLSelectElement).selectedIndex = 0;
        await select.trigger("change");
        expect(wrapper.emitted("update:active-range")).toEqual([["7d"], [undefined]]);
    });

    it("shows a disabled, selected Custom range only for a custom range", () => {
        expect(mountTarget().text()).not.toContain("Custom range");
        const custom = mountTarget("custom").findAll("option")[0]!;
        expect(custom.text()).toBe("Custom range");
        expect(custom.attributes("disabled")).toBeDefined();
        expect((custom.element as HTMLOptionElement).selected).toBe(true);
    });
});
