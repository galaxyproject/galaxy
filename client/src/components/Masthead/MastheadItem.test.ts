import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import MastheadItem from "./MastheadItem.vue";

describe("MastheadItem", () => {
    // An undeclared `click` would fall through to the BNavItem root and fire the
    // parent's handler a second time.
    it("emits click exactly once per click", async () => {
        const onClick = vi.fn();
        const wrapper = mount(MastheadItem as any, {
            props: { id: "test-item", title: "Test", tooltip: "Test item" },
            attrs: { onClick },
        });
        await wrapper.find("a").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
