import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import FormNumber from "./FormNumber.vue";

const localVue = getLocalVue();

async function mountFormNumber(propsData: object) {
    return mount(FormNumber as object, {
        localVue,
        propsData,
    });
}

describe("FormInput", () => {
    const getAlert = (wrapper: Wrapper<Vue>) => wrapper.find("[role='alert']");
    const getInput = (wrapper: Wrapper<Vue>) => wrapper.find("input[type='number']");

    it("input should be rendered with number type", async () => {
        const wrapper = await mountFormNumber({ value: 1, type: "float" });

        await flushPromises();

        const input = getInput(wrapper);
        expect(input.exists()).toBe(true);
    });

    it("input range should exist", async () => {
        async function assertRange(props: object, shouldExist: boolean) {
            const wrapper = await mountFormNumber(props);

            const inputRange = wrapper.find("input[type='range']");
            expect(inputRange.exists()).toBe(shouldExist);

            wrapper.destroy();
        }

        const props: { value: number; type: string; min?: number; max?: number } = { value: 50, type: "float" };
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
        async function checkOutOfRangeAlert(number: number) {
            const props = { value: 50, type: "float", min: 10, max: 100 };

            const wrapper = await mountFormNumber(props);

            const input = getInput(wrapper);

            await input.setValue(number);

            await input.trigger("change");

            const alert = getAlert(wrapper);
            expect(alert.exists()).toBeTruthy();
            expect(alert.text().includes(`${number} is out`)).toBeTruthy();

            wrapper.destroy();
        }

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
        async function checkFractionsAlert(key: number) {
            const props = { value: 50, type: "integer", min: 10, max: 100 };
            const wrapper = await mountFormNumber(props);

            const input = getInput(wrapper);

            await input.trigger("keydown", {
                keyCode: key,
            });

            await flushPromises();

            const alert = getAlert(wrapper);
            expect(alert.exists()).toBeTruthy();

            wrapper.destroy();
        }

        const keyCodes = [190, 110];

        for (const key of keyCodes) {
            await checkFractionsAlert(key);
        }
    });

    it("should calculate the right step for floats", async () => {
        async function expectStep(value: number | string | undefined, expectedStep: number) {
            const props = { value: value, type: "float", min: 0, max: 1 };
            const wrapper = await mountFormNumber(props);

            const input = getInput(wrapper);
            expect(input.attributes("step")).toBe(expectedStep.toString());
        }

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
            expectStep(testValues[index]?.value, testValues[index].step);
        }
    });
});
