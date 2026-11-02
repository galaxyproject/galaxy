import { mount } from "@vue/test-utils";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { configureCompat } from "vue";

import GTooltip from "./GTooltip.vue";

// Vue 3 renders a bound `false` as attr="false" instead of dropping it, which would leave
// `[data-show]` matching a hidden tooltip.
beforeAll(() => configureCompat({ ATTR_FALSE_VALUE: false }));
afterAll(() => configureCompat({ ATTR_FALSE_VALUE: true }));

describe("GTooltip", () => {
    it("sets data-show only while showing", async () => {
        const reference = document.createElement("button");
        const wrapper = mount(GTooltip, { props: { reference, text: "Hint" } });

        expect(wrapper.attributes("data-show")).toBeUndefined();

        (wrapper.vm as unknown as { show: () => void }).show();
        await wrapper.vm.$nextTick();
        expect(wrapper.attributes("data-show")).toBe("true");

        (wrapper.vm as unknown as { hide: () => void }).hide();
        await wrapper.vm.$nextTick();
        expect(wrapper.attributes("data-show")).toBeUndefined();
    });
});
