import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GDateTime from "./GDateTime.vue";

const localVue = getLocalVue(true);

async function mountGDateTime(props: object) {
    const wrapper = mount(GDateTime as object, {
        props: {
            ...props,
        },
        global: localVue,
    });

    return wrapper;
}

describe("GDateTime.vue", () => {
    it("emits updated date when input changes", async () => {
        const wrapper = await mountGDateTime({
            modelValue: new Date("1970-01-01T00:00:00"),
        });

        const dateInput = wrapper.find('input[type="date"]');
        await dateInput.setValue("2023-08-30");

        expect(wrapper.emitted()).toHaveProperty("update:modelValue");
        expect(emittedArg(wrapper, "update:modelValue")).toEqual(new Date("2023-08-30T00:00:00"));
    });

    it("emits updated time when input changes", async () => {
        const wrapper = await mountGDateTime({
            modelValue: new Date("1970-01-01T00:00:00"),
        });

        const timeInput = wrapper.find('input[type="time"]');
        await timeInput.setValue("12:30");

        expect(wrapper.emitted()).toHaveProperty("update:modelValue");
        expect(emittedArg(wrapper, "update:modelValue")).toEqual(new Date("1970-01-01T12:30:00"));
    });

    it("shows the model's date and time and follows parent updates", async () => {
        const wrapper = await mountGDateTime({
            modelValue: new Date("2024-03-05T14:07:00"),
        });

        const dateInput = wrapper.find('input[type="date"]').element as HTMLInputElement;
        const timeInput = wrapper.find('input[type="time"]').element as HTMLInputElement;
        expect(dateInput.value).toBe("2024-03-05");
        expect(timeInput.value).toBe("14:07");

        await wrapper.setProps({ modelValue: new Date("2025-12-31T09:45:00") } as object);

        expect(dateInput.value).toBe("2025-12-31");
        expect(timeInput.value).toBe("09:45");
    });

    it("keeps the time when only the date changes", async () => {
        const wrapper = await mountGDateTime({
            modelValue: new Date("2024-03-05T14:07:00"),
        });

        await wrapper.find('input[type="date"]').setValue("2023-08-30");

        expect(emittedArg(wrapper, "update:modelValue")).toEqual(new Date("2023-08-30T14:07:00"));
    });
});
