import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import IdentifierDisplay from "./IdentifierDisplay.vue";

describe("IdentifierDisplay", () => {
    // The rule builder highlights a mapping's columns while the pointer is over it.
    it("passes mouseenter and mouseleave on to the parent", async () => {
        const onMouseenter = vi.fn();
        const onMouseleave = vi.fn();
        const wrapper = mount(IdentifierDisplay as object, {
            props: { type: "list_identifiers", columns: [0], colHeaders: ["A"], onMouseenter, onMouseleave },
        });

        await wrapper.find("li").trigger("mouseenter");
        await wrapper.find("li").trigger("mouseleave");

        expect(onMouseenter).toHaveBeenCalledTimes(1);
        expect(onMouseleave).toHaveBeenCalledTimes(1);
    });
});
