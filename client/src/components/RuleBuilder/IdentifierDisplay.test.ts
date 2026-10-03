import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import IdentifierDisplay from "./IdentifierDisplay.vue";

describe("IdentifierDisplay", () => {
    // The rule builder highlights a mapping's columns while the pointer is over it.
    it("passes mouseover and mouseout on to the parent", async () => {
        const onMouseover = vi.fn();
        const onMouseout = vi.fn();
        const wrapper = mount(IdentifierDisplay as object, {
            props: { type: "list_identifiers", columns: [0], colHeaders: ["A"], onMouseover, onMouseout },
        });

        await wrapper.find("li").trigger("mouseover");
        await wrapper.find("li").trigger("mouseout");

        expect(onMouseover).toHaveBeenCalledTimes(1);
        expect(onMouseout).toHaveBeenCalledTimes(1);
    });
});
