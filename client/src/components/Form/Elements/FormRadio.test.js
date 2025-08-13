import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormRadio";

describe("FormRadio", () => {
    let wrapper;

    beforeEach(() => {
        const globalConfig = getLocalVue(true);
        wrapper = mount(MountTarget, {
            props: {
                value: false,
                options: [],
            },
            global: globalConfig.global,
        });
    });

    it("basics", async () => {
        const n = 3;
        const options = [];
        for (let i = 0; i < n; i++) {
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }
        await wrapper.setProps({ options });
        
        // Test radio button selection by setting the currentValue
        for (let i = 0; i < n; i++) {
            wrapper.vm.currentValue = `value_${i}`;
            await wrapper.vm.$nextTick();
            expect(wrapper.emitted()["input"][i][0]).toBe(`value_${i}`);
        }
    });
});
