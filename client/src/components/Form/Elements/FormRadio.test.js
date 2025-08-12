import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormRadio";

describe("FormRadio", () => {
    let wrapper;

    beforeEach(() => {
        const globalConfig = getLocalVue(true);
        wrapper = mount(MountTarget, {
            propsData: {
                value: false,
                options: [],
            },
            ...globalConfig,
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
        const labels = wrapper.findAll(".custom-control-label");
        expect(inputs.length).toBe(n);
        for (let i = 0; i < n; i++) {
            await inputs[i].setValue(true);
            expect(labels[i].text()).toBe(`label_${i}`);
            expect(inputs[i].attributes("value")).toBe(`value_${i}`);
            expect(wrapper.emitted()["input"][i][0]).toBe(`value_${i}`);
        }
    });
});
