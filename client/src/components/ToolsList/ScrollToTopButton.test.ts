import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ScrollToTopButton from "./ScrollToTopButton.vue";

// Run the component with Vue 3 listener semantics: an undeclared `click` would
// fall through to the GButton root and fire the parent's handler a second time.
const Vue3ScrollToTopButton = {
    ...ScrollToTopButton,
    compatConfig: { ...(ScrollToTopButton as any).compatConfig, INSTANCE_LISTENERS: false },
};

describe("ScrollToTopButton", () => {
    it("emits click exactly once per click under Vue 3 listener semantics", async () => {
        const onClick = vi.fn();
        const wrapper = mount(Vue3ScrollToTopButton as any, {
            props: { offset: 500 },
            attrs: { onClick },
        });
        await wrapper.find("button").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
