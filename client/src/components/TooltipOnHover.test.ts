import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TooltipOnHover from "./TooltipOnHover.vue";

// Vue 3 renders a bound `false` as disabled="false", and v-g-tooltip treats any `disabled`
// attribute on the host as "don't show". compat-config.js turns ATTR_FALSE_VALUE off.

describe("TooltipOnHover", () => {
    it("leaves disabled off an enabled host", () => {
        const wrapper = mount(TooltipOnHover as object, { props: { title: "Finish" } });

        expect(wrapper.attributes("disabled")).toBeUndefined();
    });

    it("marks a disabled host", () => {
        const wrapper = mount(TooltipOnHover as object, { props: { title: "Finish", disabled: true } });

        expect(wrapper.attributes("disabled")).toBeDefined();
    });
});
