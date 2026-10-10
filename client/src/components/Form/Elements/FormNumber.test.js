import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import FormNumber from "./FormNumber.vue";

enableAutoUnmount(afterEach);

function mountFormNumber(props) {
    return shallowMount(FormNumber, {
        props,
        global: {
            ...getLocalVue(),
            stubs: { BRow: false, BCol: false, BFormInput: false, GAlert: false },
        },
    });
}

const NUMBER_INPUT = "input[type='number']";
const RANGE_INPUT = "input[type='range']";

describe("FormNumber", () => {
    it.each(["float", "integer"])("renders a number input for %s values", (type) => {
        const wrapper = mountFormNumber({ value: 1, type });
        expect(wrapper.find(NUMBER_INPUT).exists()).toBe(true);
    });

    it.each([
        { name: "no bounds", bounds: {}, hasRange: false },
        { name: "only a minimum", bounds: { min: 1 }, hasRange: false },
        { name: "increasing bounds", bounds: { min: 1, max: 100 }, hasRange: true },
        { name: "a zero minimum", bounds: { min: 0, max: 100 }, hasRange: true },
        { name: "a maximum below the minimum", bounds: { min: 0, max: -100 }, hasRange: false },
    ])("renders a slider: $name", ({ bounds, hasRange }) => {
        const wrapper = mountFormNumber({ value: 50, type: "float", ...bounds });
        expect(wrapper.find(RANGE_INPUT).exists()).toBe(hasRange);
    });

    it.each([1, 0, -1, Number.MIN_VALUE, 110, Number.MAX_VALUE])(
        "warns when %s is outside the range 10–100",
        async (value) => {
            const wrapper = mountFormNumber({ value: 50, type: "float", min: 10, max: 100 });
            const input = wrapper.find(NUMBER_INPUT);
            await input.setValue(value);
            await input.trigger("change");

            const alert = wrapper.find(".alert");
            expect(alert.exists()).toBe(true);
            expect(alert.text()).toContain(`${value} is out`);
        },
    );

    it("warns when a decimal point is entered into a bounded integer input", async () => {
        const wrapper = mountFormNumber({ value: 50, type: "integer", min: 10, max: 100 });
        await wrapper.find(NUMBER_INPUT).trigger("keypress", { key: "." });
        expect(wrapper.find(".alert").exists()).toBe(true);
    });

    it.each([
        { name: "decimal points in integer inputs", type: "integer", key: ".", bounds: {}, blocked: true },
        { name: "decimal points in float inputs", type: "float", key: ".", bounds: {}, blocked: false },
        { name: "minus signs without a minimum", type: "float", key: "-", bounds: {}, blocked: false },
        {
            name: "minus signs with a non-negative minimum",
            type: "float",
            key: "-",
            bounds: { min: 0, max: 100 },
            blocked: true,
        },
    ])("validates $name", async ({ type, key, bounds, blocked }) => {
        const wrapper = mountFormNumber({ value: "", type, ...bounds });
        const preventDefault = vi.fn();
        await wrapper.find(NUMBER_INPUT).trigger("keypress", { key, preventDefault });

        if (blocked) {
            expect(preventDefault).toHaveBeenCalled();
        } else {
            expect(preventDefault).not.toHaveBeenCalled();
        }
    });

    it.each([
        { name: "undefined", value: undefined, step: "0.1" },
        { name: "empty string", value: "", step: "0.1" },
        { name: "zero", value: 0, step: "0.1" },
        { name: "one decimal place", value: 0.5, step: "0.1" },
        { name: "two decimal places", value: 0.55, step: "0.01" },
        { name: "three decimal places", value: 0.555, step: "0.001" },
        { name: "four decimal places", value: 0.5555, step: "0.001" },
        { name: "scientific notation", value: 25e-100, step: "0.001" },
    ])("sets the rendered float step for $name", ({ value, step }) => {
        const wrapper = mountFormNumber({ value, type: "float", min: 0, max: 1 });
        expect(wrapper.find(NUMBER_INPUT).attributes("step")).toBe(step);
        expect(wrapper.find(RANGE_INPUT).attributes("step")).toBe(step);
    });
});
