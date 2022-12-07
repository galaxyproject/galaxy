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

    it("Confirm 'n + 1' checkboxes created (eg. includes the Select-All). Confirm labels and values match. Confirm correct values emitted.", async () => {
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
        const expectedValues = [];
        for (let i = 0; i < n; i++) {
            await inputs.at(i + 1).setChecked();
            expect(labels.at(i + 1).text()).toBe(`label_${i}`);
            expect(inputs.at(i + 1).attributes("value")).toBe(`value_${i}`);
            expectedValues.push(`value_${i}`);
            expect(wrapper.emitted()["input"][i][0]).toEqual(expectedValues);
        }
    });
    it("Confirm checkboxes are created when various 'empty values' are passed.", async () => {
        const emptyValues = [0, null, false, true, undefined];
        const options = [];
        for (let i = 0; i < emptyValues.length; i++) {
            options.push([`label_${i}`, emptyValues[i]]);
        }
        await wrapper.setProps({ options });
        const inputs = wrapper.findAll("[type='checkbox']");
        expect(inputs.length).toBe(emptyValues.length + 1);
        const expectedValues = [];
        for (let i = 0; i < emptyValues; i++) {
            await inputs.at(i + 1).setChecked();
            expect(inputs.at(i + 1).attributes("value")).toBe(emptyValues[i]);
            expectedValues.push(expectedValues[i]);
            expect(wrapper.emitted()["input"][i][0]).toEqual(expectedValues);
        }
    });
});
