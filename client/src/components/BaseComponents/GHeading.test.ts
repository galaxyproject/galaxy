import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GHeading from "../Common/Heading.vue";

describe("collapsible headings", () => {
    it.each([false, true])("names the toggle and keeps its state in sync (separator=%s)", async (separator) => {
        const wrapper = mount(GHeading, {
            global: getLocalVue(),
            props: { collapse: "closed", separator },
            slots: { default: "Installation options" },
        });
        const toggle = wrapper.get("button");
        expect(toggle.attributes("aria-label")).toBe("Expand section");
        expect(toggle.attributes("aria-expanded")).toBe("false");
        await toggle.trigger("click");
        expect(wrapper.emitted("click")).toHaveLength(1);
        await wrapper.setProps({ collapse: "open" });
        expect(toggle.attributes("aria-label")).toBe("Collapse section");
        expect(toggle.attributes("aria-expanded")).toBe("true");
        wrapper.unmount();
    });
});
