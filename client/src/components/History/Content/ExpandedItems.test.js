import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { h } from "vue";

import ExpandedItems from "./ExpandedItems";

const localVue = getLocalVue();

describe("ExpandedItems", () => {
    it("hands its expansion helpers to the default slot without $scopedSlots", async () => {
        const item = { id: "item_id" };
        const wrapper = mount(ExpandedItems, {
            props: { scopeKey: "history_id", getItemKey: (i) => i.id },
            slots: {
                default: ({ isExpanded, setExpanded, expandedCount }) =>
                    h("button", { onClick: () => setExpanded(item, !isExpanded(item)) }, String(expandedCount)),
            },
            global: localVue,
        });

        expect(wrapper.find("button").text()).toBe("0");
        await wrapper.find("button").trigger("click");
        expect(wrapper.find("button").text()).toBe("1");
    });
});
