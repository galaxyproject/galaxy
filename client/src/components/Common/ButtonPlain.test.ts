import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import ButtonPlain from "./ButtonPlain.vue";

// Run the component with Vue 3 listener semantics: an undeclared `click` would
// fall through to the root div and fire the parent's handler a second time.
const Vue3ButtonPlain: any = {
    ...ButtonPlain,
    compatConfig: { ...(ButtonPlain as any).compatConfig, INSTANCE_LISTENERS: false },
};

function mountWithClickHandler() {
    const onClick = vi.fn();
    const Parent = defineComponent({
        render: () => h(Vue3ButtonPlain, { onClick }, () => "label"),
    });
    const wrapper = mount(Parent);
    return { wrapper, onClick };
}

describe("ButtonPlain", () => {
    it("calls the parent's click handler once per mouse click", async () => {
        const { wrapper, onClick } = mountWithClickHandler();
        await wrapper.find("[role='button']").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("calls the parent's click handler once for Enter and Space", async () => {
        const { wrapper, onClick } = mountWithClickHandler();
        const button = wrapper.find("[role='button']");
        await button.trigger("keydown", { key: "Enter" });
        await button.trigger("keydown", { key: " " });
        expect(onClick).toHaveBeenCalledTimes(2);
    });
});
