import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import MountTarget from "./FormCheck";

const localVue = getLocalVue(true);

describe("FormCheck", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(MountTarget, {
            propsData: {
                value: null,
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
        expect(inputs.length).toBe(n + 1);
        let value = [];
        for (let i = 0; i < n; i++) {
            const j = i + 1;
            await inputs.at(j).setChecked();
            expect(labels.at(j).text()).toBe(`label_${i}`);
            expect(inputs.at(j).attributes("value")).toBe(`value_${i}`);
            value = [...value, `value_${i}`];
            expect(wrapper.emitted()["input"][i][0]).toEqual(value);
        }
    });
});
