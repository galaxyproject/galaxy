import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import IdentifierDisplay from "./IdentifierDisplay.vue";

describe("IdentifierDisplay", () => {
    enableAutoUnmount(afterEach);

    // The rule builder highlights a mapping's columns while the pointer is over it.
    it("passes mouseover and mouseout on to the parent", async () => {
        const onMouseover = vi.fn();
        const onMouseout = vi.fn();
        const wrapper = mount(IdentifierDisplay, {
            props: { type: "list_identifiers", columns: [0], colHeaders: ["A"], onMouseover, onMouseout },
        });

        await wrapper.get("li").trigger("mouseover");
        await wrapper.get("li").trigger("mouseout");

        expect(onMouseover).toHaveBeenCalledTimes(1);
        expect(onMouseout).toHaveBeenCalledTimes(1);
    });
});
