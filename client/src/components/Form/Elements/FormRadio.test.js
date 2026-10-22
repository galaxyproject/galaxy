import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import MountTarget from "./FormRadio.vue";

const localVue = getLocalVue(true);

describe("FormRadio", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            props: {
                value: false,
                options: [],
            },
            global: localVue,
        });
    });

    it("basics", async () => {
        const noInput = wrapper.find("[type='radio']");
        expect(noInput.exists()).toBe(false);
        const n = 3;
        const options = [];
        for (let i = 0; i < n; i++) {
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }
        await wrapper.setProps({ options });
        const inputs = wrapper.findAll("[type='radio']");
        const labels = wrapper.findAll(".g-radio-label");
        expect(inputs.length).toBe(n);
        expect(new Set(inputs.map((input) => input.attributes("name"))).size).toBe(1);
        for (let i = 0; i < n; i++) {
            await inputs.at(i).setValue(true);
            expect(labels.at(i).text()).toBe(`label_${i}`);
            expect(inputs.at(i).attributes("value")).toBe(`value_${i}`);
            expect(emittedArg(wrapper, "input", i)).toBe(`value_${i}`);
        }
    });

    it("names the radio group by the given label id", async () => {
        await wrapper.setProps({ options: [{ label: "label_0", value: "value_0" }] });
        expect(wrapper.find("fieldset").attributes("aria-labelledby")).toBeUndefined();
        await wrapper.setProps({ ariaLabelledby: "title-id" });
        expect(wrapper.find("fieldset").attributes("aria-labelledby")).toBe("title-id");
    });
});
