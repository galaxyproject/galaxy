import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import MountTarget from "./FormCheck.vue";

const localVue = getLocalVue(true);

describe("FormCheck", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(MountTarget as object, {
            propsData: {
                value: [],
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
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }

        await wrapper.setProps({ options });

        const inputs = wrapper.findAll("[type='checkbox']");
        const labels = wrapper.findAll(".custom-control-label");
        expect(inputs.length).toBe(n + 1);
        expect(labels.length).toBe(n + 1);

        let expectedValues: string[] | undefined | null = [];

        for (let i = 0; i < n; i++) {
            await inputs.at(i + 1).setChecked();

            expect(labels.at(i + 1).text()).toBe(`label_${i}`);
            expect(inputs.at(i + 1).attributes("value")).toBe(`value_${i}`);

            expectedValues.push(`value_${i}`);

            await flushPromises();

            expect(wrapper.emitted()).toHaveProperty("input");
            expect(wrapper.emitted()["input"]?.[i]?.[0]).toEqual(expectedValues);
        }

        for (let i = 0; i < n; i++) {
            await inputs.at(i + 1).setChecked(false);

            expectedValues = expectedValues?.slice(1);

            if (expectedValues?.length === 0) {
                expectedValues = null;
            }

            expect(wrapper.emitted().input?.[i + 3]?.[0]).toEqual(expectedValues);
        }
    });

    it("Confirm checkboxes are created when various 'empty values' are passed.", async () => {
        const emptyValues = [0, null, false, true, undefined];
        const options = [];

        for (let i = 0; i < emptyValues.length; i++) {
            options.push({ label: `label_${i}`, value: emptyValues[i] });
        }

        await wrapper.setProps({ options });

        const inputs = wrapper.findAll("[type='checkbox']");
        expect(inputs.length).toBe(emptyValues.length + 1);

        const expectedValues = [];

        for (let i = 0; i < emptyValues.length; i++) {
            await inputs.at(i + 1).setChecked();

            expect(inputs.at(i + 1).attributes("value")).toBe(emptyValues[i]);
            expectedValues.push(emptyValues[i]);
            expect(wrapper.emitted()?.["input"]?.[i]?.[0]).toEqual(expectedValues);
        }
    });

    it("Confirm Select-All checkbox works in various states: select-all, unselect-all, indeterminate/partial-list-selection.", async () => {
        const n = 3;
        const options = [];

        for (let i = 0; i < n; i++) {
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }

        await wrapper.setProps({ options });

        const inputs = wrapper.findAll("[type='checkbox']");

        /* confirm number of checkboxes requested matches number checkboxes created */
        expect(inputs.length).toBe(n + 1);

        /* confirm component loads unchecked */
        for (let i = 0; i < n + 1; i++) {
            expect((inputs.at(i).element as HTMLInputElement).checked).toBeFalsy();
        }

        /* 1 - confirm select-all option checked */
        await inputs.at(0).setChecked();
        expect((inputs.at(0).element as HTMLInputElement).checked).toBeTruthy();

        /* ...confirm corresponding options checked */
        const values = options.map((option) => option.value);
        expect(wrapper.emitted()?.["input"]?.[0]?.[0]).toStrictEqual(values);

        /* 2 - confirm select-all option UNchecked */
        await inputs.at(0).setChecked(false);
        expect((inputs.at(0).element as HTMLInputElement).checked).toBeFalsy();

        /* ...confirm corresponding options UNchecked */
        for (let i = 0; i < n; i++) {
            expect((inputs.at(i + 1).element as HTMLInputElement).checked).toBeFalsy();
        }

        /* 3 - confirm corresponding options indeterminate-state */
        await inputs.at(1).setChecked(true);
        expect(wrapper.emitted()?.input?.[2]?.[0]).toStrictEqual(["value_0"]);

        await wrapper.setProps({ value: ["value_0"] });
        expect((inputs.at(0).element as HTMLInputElement).indeterminate).toBe(true);
    });
});
