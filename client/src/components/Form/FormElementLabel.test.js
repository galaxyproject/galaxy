import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import Target from "./FormElementLabel.vue";

const localVue = getLocalVue();

function mountTarget(props = {}, slots = {}) {
    return mount(Target, {
        localVue,
        propsData: props,
        slots,
        stubs: {
            FontAwesomeIcon: true,
        },
        directives: {
            localize: () => {},
        },
    });
}

describe("FormElementLabel.vue", () => {
    it("should render title", () => {
        const wrapper = mountTarget({
            title: "Form Label",
            required: false,
        });
        expect(wrapper.text()).toContain("Form Label");
    });

    it("should render help text", () => {
        const wrapper = mountTarget({
            title: "Test",
            help: "Helpful info",
            required: false,
        });
        expect(wrapper.text()).toContain("Helpful info");
    });

    it("should render check icon if condition and required are true", () => {
        const wrapper = mountTarget({
            title: "Check Label",
            required: true,
            condition: true,
        });
        const asterisk = wrapper.find("small");
        expect(asterisk.exists()).toBe(true);
        expect(asterisk.text()).toBe("*");
    });

    it("should render asterisk if required is true and condition is false", () => {
        const wrapper = mountTarget({
            title: "Asterisk Label",
            required: true,
            condition: false,
        });
        const asterisk = wrapper.find("small.text-danger");
        expect(asterisk.exists()).toBe(true);
        expect(asterisk.text()).toBe("* required");
    });

    it("should render nothing extra if required is false", () => {
        const wrapper = mountTarget({
            title: "No Symbol",
            required: false,
        });
        expect(wrapper.findComponent({ name: "FontAwesomeIcon" }).exists()).toBe(false);
        expect(wrapper.find("span.text-danger").exists()).toBe(false);
    });

    it("should render slot content", () => {
        const wrapper = mountTarget(
            {
                title: "Slot Test",
                required: false,
            },
            {
                default: "<div class='slot-content'>Hello Slot</div>",
            }
        );
        expect(wrapper.find(".slot-content").exists()).toBe(true);
        expect(wrapper.text()).toContain("Hello Slot");
    });
});
