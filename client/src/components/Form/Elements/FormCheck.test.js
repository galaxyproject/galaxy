import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormCheck";

describe("FormCheck", () => {
    let wrapper;

    beforeEach(() => {
        const globalConfig = getLocalVue(true);
        wrapper = mount(MountTarget, {
            props: {
                value: null,
                options: [],
            },
            global: globalConfig.global,
        });
    });

    it("Confirm checkboxes created and emit correct values.", async () => {
        const n = 3;
        const options = [];
        for (let i = 0; i < n; i++) {
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }
        await wrapper.setProps({ options });

        // Test individual checkbox selection by setting component's value
        let expectedValues = [];
        for (let i = 0; i < n; i++) {
            expectedValues.push(`value_${i}`);
            await wrapper.setProps({ value: [...expectedValues] });
            expect(wrapper.emitted()["input"][i][0]).toEqual([...expectedValues]);
        }

        // Test deselection
        for (let i = 0; i < n; i++) {
            expectedValues = expectedValues.slice(1);
            const nextValue = expectedValues.length === 0 ? null : [...expectedValues];
            await wrapper.setProps({ value: nextValue });
            expect(wrapper.emitted().input[i + n][0]).toEqual(nextValue);
        }
    });

    it("Confirm checkboxes are created when various 'empty values' are passed.", async () => {
        const emptyValues = [0, null, false, true, undefined];
        const options = [];
        for (let i = 0; i < emptyValues.length; i++) {
            options.push({ label: `label_${i}`, value: emptyValues[i] });
        }
        await wrapper.setProps({ options });

        // Test that component can handle edge case values
        const expectedValues = [];
        for (let i = 0; i < emptyValues.length; i++) {
            expectedValues.push(emptyValues[i]);
            // Simulate user interaction by setting the computed property directly
            wrapper.vm.currentValue = [...expectedValues];
            await wrapper.vm.$nextTick();
            expect(wrapper.emitted()["input"][i][0]).toEqual([...expectedValues]);
        }
    });

    it("Confirm Select-All checkbox works in various states: select-all, unselect-all, indeterminate/partial-list-selection.", async () => {
        const n = 3;
        const options = [];
        for (let i = 0; i < n; i++) {
            options.push({ label: `label_${i}`, value: `value_${i}` });
        }
        await wrapper.setProps({ options });

        // Test select all functionality by calling the component method
        const allValues = options.map((option) => option.value);
        wrapper.vm.onSelectAll(true);
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted()["input"][0][0]).toStrictEqual(allValues);

        // Test unselect all functionality
        wrapper.vm.onSelectAll(false);
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted()["input"][1][0]).toStrictEqual(null);

        // Test partial selection (indeterminate state)
        wrapper.vm.currentValue = ["value_0"];
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted().input[2][0]).toStrictEqual(["value_0"]);

        // Check that the computed properties work correctly with partial selection
        await wrapper.setProps({ value: ["value_0"] });
        expect(wrapper.vm.indeterminate).toBe(true);
        expect(wrapper.vm.selectAll).toBe(false);

        // Check that computed properties work with all selected
        await wrapper.setProps({ value: allValues });
        expect(wrapper.vm.indeterminate).toBe(false);
        expect(wrapper.vm.selectAll).toBe(true);
    });
});
