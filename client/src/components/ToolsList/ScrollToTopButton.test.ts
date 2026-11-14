import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ScrollToTopButton from "./ScrollToTopButton.vue";

describe("ScrollToTopButton", () => {
    // An undeclared `click` would fall through to the GButton root and fire the
    // parent's handler a second time.
    it("emits click exactly once per click", async () => {
        const onClick = vi.fn();
        const wrapper = mount(ScrollToTopButton as any, {
            props: { offset: 500 },
            attrs: { onClick },
        });
        await wrapper.find("button").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
