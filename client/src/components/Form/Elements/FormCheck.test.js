import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import MountTarget from "./FormCheck";

const localVue = getLocalVue(true);

describe("FormCheck", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            propsData: {
                value: false,
                options: [],
            },
            localVue,
        });
    });

    it("basics", async () => {
        const noInput = wrapper.find("[type='checkbox']");
        expect(noInput.exists()).toBe(false);
        const n = 3;
        const options = [];
        for (let i = 0; i < n; i++) {
            options.push([`label_${i}`, `value_${i}`]);
        }
        await wrapper.setProps({ options });
        const inputs = wrapper.findAll("[type='checkbox']");
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
