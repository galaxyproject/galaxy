import { getLocalVue } from "@tests/vitest/helpers";
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
        const labels = wrapper.findAll(".custom-control-label");
        expect(inputs.length).toBe(n);
        for (let i = 0; i < n; i++) {
            await inputs.at(i).setChecked();
            expect(labels.at(i).text()).toBe(`label_${i}`);
            expect(inputs.at(i).attributes("value")).toBe(`value_${i}`);
            expect(wrapper.emitted()["input"][i][0]).toBe(`value_${i}`);
        }
    });
});
