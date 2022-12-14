import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import FormNumber from "./FormNumber";

const localVue = getLocalVue();

describe("FormInput", () => {
    const mountFormNumber = async (props) =>
        await mount(FormNumber, {
            propsData: props,
            localVue,
        });

    const getInput = async (wrapper) => await wrapper.find("input[type='number']");
    const getInputRange = async (wrapper) => await wrapper.find("input[type='range']");
    const getAlert = async (wrapper) => await wrapper.find("[role='alert']");

    it("input should be rendered with number type", async () => {
        const wrapper = await mountFormNumber({ value: 1, type: "float" });
        await flushPromises();
        const input = await getInput(wrapper);
        expect(input.exists()).toBe(true);
    });

    it("input range should exist", async () => {
        const assertRange = async (props, shoudExist) => {
            const wrapper = await mountFormNumber(props);

            const inputRange = await getInputRange(wrapper);
            expect(inputRange.exists()).toBe(shoudExist);
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

    it("range should be respected", async () => {
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

    it("type should be expected", async () => {
        const checkFractionsAlert = async (key) => {
            const wrapper = await mountFormNumber(props);
            const input = await getInput(wrapper);

            await input.trigger("keydown", {
                keyCode: key,
            });

            await flushPromises();

            const alert = await getAlert(wrapper);
            expect(alert.exists()).toBeTruthy();
            wrapper.destroy();
        };

        const props = { value: 50, type: "integer", min: 10, max: 100 };
        const keycodes = [190, 110];

        for (const key of keycodes) {
            await checkFractionsAlert(key);
        }
    });

    it("should calculate the right step for floats", async () => {
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
