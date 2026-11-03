import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import GDateTime from "./GDateTime.vue";

const localVue = getLocalVue(true);
enableAutoUnmount(afterEach);

function mountDateTime(value: Date) {
    return mount(GDateTime, { props: { value }, global: localVue });
}

describe("GDateTime.vue", () => {
    it.each([
        { field: "date", inputValue: "2023-08-30", expectedValue: "2023-08-30T00:00:00" },
        { field: "time", inputValue: "12:30", expectedValue: "1970-01-01T12:30:00" },
    ])("emits the updated $field when its input changes", async ({ field, inputValue, expectedValue }) => {
        const wrapper = mountDateTime(new Date("1970-01-01T00:00:00"));
        await wrapper.get(`input[type="${field}"]`).setValue(inputValue);

        expect(wrapper.emitted()).toHaveProperty("input");
        expect(emittedArg(wrapper, "input")).toEqual(new Date(expectedValue));
    });
});
