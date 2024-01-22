import { shallowMount } from "@vue/test-utils";
import { format, parseISO } from "date-fns";
import { getLocalVue } from "tests/jest/helpers";

import UtcDate from "./UtcDate.vue";

describe("UTCDate component", () => {
    const localVue = getLocalVue();

    it("Loads a date in default mode, can format outputs as expected.", async () => {
        const wrapper = shallowMount(UtcDate, {
            propsData: { date: "2015-10-21T16:29:00.000000" },
            localVue,
        });
        expect(wrapper.text()).toBe("2015-10-21T16:29:00.000Z");

        await wrapper.setProps({ mode: "elapsed" });
        expect(wrapper.text()).toContain("years ago");

        await wrapper.setProps({ mode: "pretty" });
        expect(wrapper.text()).toBe(format(parseISO("2015-10-21T16:29:00.000Z"), "eeee MMM do H:mm:ss yyyy zz"));
    });
});
