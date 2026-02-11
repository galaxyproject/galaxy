import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import FormNumber from "./FormNumber.vue";

const localVue = getLocalVue();

describe("FormNumber", () => {
    const mountFormNumber = async (props) =>
        await mount(FormNumber, {
            propsData: props,
            localVue,
        });

    const getInput = async (wrapper) => await wrapper.find("input[type='number']");
    const getInputRange = async (wrapper) => await wrapper.find("input[type='range']");
    const getAlert = async (wrapper) => await wrapper.find("[role='alert']");

    it("renders a number input with appropriate type", async () => {
        const wrapperFloat = await mountFormNumber({ value: 1, type: "float" });
        const inputFloat = await getInput(wrapperFloat);
        expect(inputFloat.exists()).toBe(true);
        wrapperFloat.destroy();

        const wrapperInteger = await mountFormNumber({ value: 1, type: "integer" });
        const inputInteger = await getInput(wrapperInteger);
        expect(inputInteger.exists()).toBe(true);
        wrapperInteger.destroy();
    });

    it("renders a range input only when both min and max are defined and max > min", async () => {
        const assertRange = async (props, shouldExist) => {
            const wrapper = await mountFormNumber(props);

            const inputRange = await getInputRange(wrapper);
            expect(inputRange.exists()).toBe(shouldExist);
            wrapper.destroy();
        };

        const props = { value: 50, type: "float" };
        // if min or max is not defined, range shouldn't be rendered
        await assertRange(props, false);
        props.min = 1;
        await assertRange(props, false);
        props.max = 100;
        await assertRange(props, true);
        // test usecase: range should be rendered on 0
        props.min = 0;
        await assertRange(props, true);
        // test usecase: if max < min range shouldn't be rendered
        props.max = -100;
        await assertRange(props, false);
    });

    it("shows an alert when the entered value is outside the defined min/max range", async () => {
        const checkOutOfRangeAlert = async (number) => {
            const props = { value: 50, type: "float", min: 10, max: 100 };
            const wrapper = await mountFormNumber(props);
            const input = await getInput(wrapper);
            await input.setValue(number);
            await input.trigger("change");
            const alert = await getAlert(wrapper);
            expect(alert.exists()).toBeTruthy();
            expect(alert.text().includes(`${number} is out`)).toBeTruthy();
            wrapper.destroy();
        };

        const numberBiggerThanRange = [110, Number.MAX_VALUE];
        const numberSmallerThanRange = [1, 0, -1, Number.MIN_VALUE];

        //alert should be shown
        for (const value of numberSmallerThanRange) {
            await checkOutOfRangeAlert(value);
        }
        for (const value of numberBiggerThanRange) {
            await checkOutOfRangeAlert(value);
        }
    });

    it("shows a validation alert when entering a decimal for integer type", async () => {
        const checkFractionsAlert = async (key) => {
            const wrapper = await mountFormNumber(props);
            const input = await getInput(wrapper);

            await input.trigger("keypress", {
                key: key,
            });

            await flushPromises();

            const alert = await getAlert(wrapper);
            expect(alert.exists()).toBeTruthy();
            wrapper.destroy();
        };

        const props = { value: 50, type: "integer", min: 10, max: 100 };
        const keys = ["."];

        for (const key of keys) {
            await checkFractionsAlert(key);
        }
    });

    it("blocks '.' for integer type", async () => {
        const integerWrapper = await mountFormNumber({ value: "", type: "integer" });
        const integerInput = await getInput(integerWrapper);

        const preventDefaultInteger = jest.fn();
        await integerInput.trigger("keypress", {
            key: ".",
            preventDefault: preventDefaultInteger,
        });

        expect(preventDefaultInteger).toHaveBeenCalled();
        integerWrapper.destroy();
    });

    it("allows '.' for float type", async () => {
        const floatWrapper = await mountFormNumber({ value: "", type: "float" });
        const floatInput = await getInput(floatWrapper);

        const preventDefaultFloat = jest.fn();
        await floatInput.trigger("keypress", {
            key: ".",
            preventDefault: preventDefaultFloat,
        });

        expect(preventDefaultFloat).not.toHaveBeenCalled();
        floatWrapper.destroy();
    });

    it("allows typing '-' when negative numbers are permitted", async () => {
        const props = { value: "", type: "float" };
        const wrapper = await mountFormNumber(props);
        const input = await getInput(wrapper);

        const preventDefault = jest.fn();
        await input.trigger("keypress", {
            key: "-",
            preventDefault,
        });

        expect(preventDefault).not.toHaveBeenCalled();
        wrapper.destroy();
    });

    it("blocks typing '-' when min is non-negative", async () => {
        const props = { value: "", type: "float", min: 0, max: 100 };
        const wrapper = await mountFormNumber(props);
        const input = await getInput(wrapper);

        const preventDefault = jest.fn();
        await input.trigger("keypress", {
            key: "-",
            preventDefault,
        });

        expect(preventDefault).toHaveBeenCalled();
        wrapper.destroy();
    });

    it("computes the correct step value based on float precision", async () => {
        const expectStep = async (value, expectedStep) => {
            const props = { value: value, type: "float", min: 0, max: 1 };
            const wrapper = await mountFormNumber(props);
            expect(wrapper.vm.step).toBe(expectedStep);
        };

        //minimum step 0.1 - maximum step 0.001
        const testValues = [
            { value: undefined, step: 0.1 },
            { value: "", step: 0.1 },
            { value: 0, step: 0.1 },
            { value: 0.5, step: 0.1 },
            { value: 0.55, step: 0.01 },
            { value: 0.555, step: 0.001 },
            { value: 0.5555, step: 0.001 },
            { value: 25e-100, step: 0.001 },
        ];
        for (let index = 0; index < testValues.length; index++) {
            expectStep(testValues[index].value, testValues[index].step);
        }
    });
});
