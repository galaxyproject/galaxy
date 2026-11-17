import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import MastheadItem from "./MastheadItem.vue";

// Run the component with Vue 3 listener semantics: an undeclared `click` would
// fall through to the BNavItem root and fire the parent's handler a second time.
const Vue3MastheadItem = {
    ...MastheadItem,
    compatConfig: { ...(MastheadItem as any).compatConfig, INSTANCE_LISTENERS: false },
};

describe("MastheadItem", () => {
    it("emits click exactly once per click under Vue 3 listener semantics", async () => {
        const onClick = vi.fn();
        const wrapper = mount(Vue3MastheadItem as any, {
            props: { id: "test-item", title: "Test", tooltip: "Test item" },
            attrs: { onClick },
        });
        await wrapper.find("a").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
