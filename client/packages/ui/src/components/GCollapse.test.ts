import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GCollapse from "./GCollapse.vue";

async function mountCollapse(visible: boolean, slot = "details") {
    const wrapper = mount(GCollapse, { props: { visible }, slots: { default: slot } });
    await flushPromises();
    return wrapper;
}

async function setVisible(wrapper: Awaited<ReturnType<typeof mountCollapse>>, visible: boolean) {
    await wrapper.setProps({ visible });
    await flushPromises();
}

describe("GCollapse", () => {
    it("is shown only once the open transition ends", async () => {
        const wrapper = await mountCollapse(false);

        await setVisible(wrapper, true);
        expect(wrapper.classes()).toContain("g-collapse-open");
        expect(wrapper.classes()).not.toContain("g-collapse-shown");

        await wrapper.trigger("transitionend");
        expect(wrapper.classes()).toContain("g-collapse-shown");
    });

    it("ignores transitionend from child elements", async () => {
        const wrapper = await mountCollapse(false, '<div class="child">details</div>');

        await setVisible(wrapper, true);
        await wrapper.get(".child").trigger("transitionend");
        expect(wrapper.classes()).not.toContain("g-collapse-shown");

        await wrapper.trigger("transitionend");
        expect(wrapper.classes()).toContain("g-collapse-shown");
    });

    it("stops being shown once it starts closing", async () => {
        const wrapper = await mountCollapse(true);
        expect(wrapper.classes()).toContain("g-collapse-shown");

        await setVisible(wrapper, false);
        expect(wrapper.classes()).not.toContain("g-collapse-shown");

        await wrapper.trigger("transitionend");
        expect(wrapper.classes()).not.toContain("g-collapse-shown");
    });
});
