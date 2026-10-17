import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import FormElementLabel from "./FormElementLabel.vue";

enableAutoUnmount(afterEach);

function mountLabel(props = {}, slots = {}) {
    return mount(FormElementLabel, {
        global: getLocalVue(),
        props,
        slots,
    });
}

describe("FormElementLabel.vue", () => {
    it("renders the title", () => {
        const wrapper = mountLabel({
            title: "Form Label",
            required: false,
        });
        expect(wrapper.text()).toContain("Form Label");
    });

    it("renders help text", () => {
        const wrapper = mountLabel({
            title: "Test",
            help: "Helpful info",
            required: false,
        });
        expect(wrapper.text()).toContain("Helpful info");
    });

    it("renders an asterisk when required and condition are true", () => {
        const wrapper = mountLabel({
            title: "Check Label",
            required: true,
            condition: true,
        });
        const asterisk = wrapper.find("small");
        expect(asterisk.exists()).toBe(true);
        expect(asterisk.text()).toBe("*");
    });

    it("renders a danger asterisk and required label when condition is false", () => {
        const wrapper = mountLabel({
            title: "Asterisk Label",
            required: true,
            condition: false,
        });
        const asterisk = wrapper.find("small.text-danger");
        expect(asterisk.exists()).toBe(true);
        expect(asterisk.text()).toContain("*");
        expect(asterisk.text()).toContain("required");
    });

    it("omits requirement indicators when not required", () => {
        const wrapper = mountLabel({
            title: "No Symbol",
            required: false,
        });
        expect(wrapper.findComponent({ name: "FontAwesomeIcon" }).exists()).toBe(false);
        expect(wrapper.text()).toContain("No Symbol");
        expect(wrapper.find("small.align-top").exists()).toBe(false);
        expect(wrapper.find("small.text-danger").exists()).toBe(false);
    });

    it("renders default slot content", () => {
        const wrapper = mountLabel(
            {
                title: "Slot Test",
                required: false,
            },
            {
                default: "<div class='slot-content'>Hello Slot</div>",
            },
        );
        expect(wrapper.find(".slot-content").exists()).toBe(true);
        expect(wrapper.text()).toContain("Hello Slot");
    });
});
