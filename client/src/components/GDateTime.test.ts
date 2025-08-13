import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";

import GDateTime from "./GDateTime.vue";

const globalConfig = getLocalVue(true);

async function mountGDateTime(props: object) {
    const wrapper = mount(GDateTime as object, {
        props: {
            ...props,
        },
        global: globalConfig.global,
    });

    return wrapper;
}

describe("GDateTime.vue", () => {
    it("emits updated date when input changes", async () => {
        const wrapper = await mountGDateTime({
            value: new Date("1970-01-01T00:00:00"),
        });

        const dateInput = wrapper.find('input[type="date"]');
        await dateInput.setValue("2023-08-30");

        expect(wrapper.emitted()).toHaveProperty("input");
        const emittedInput = wrapper.emitted("input");
        expect(emittedInput?.[0]?.[0] as Date).toEqual(new Date("2023-08-30T00:00:00"));
    });

    it("emits updated time when input changes", async () => {
        const wrapper = await mountGDateTime({
            value: new Date("1970-01-01T00:00:00"),
        });

        const timeInput = wrapper.find('input[type="time"]');
        await timeInput.setValue("12:30");

        expect(wrapper.emitted()).toHaveProperty("input");
        const emittedInput = wrapper.emitted("input");
        expect(emittedInput?.[0]?.[0] as Date).toEqual(new Date("1970-01-01T12:30:00"));
    });
});
