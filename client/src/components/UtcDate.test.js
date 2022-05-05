import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import UtcDate from "./UtcDate.vue";

describe("UTCDate component", () => {
    const localVue = getLocalVue();

    it("Loads a date in default mode, can format outputs as expected.", () => {
        const wrapper = shallowMount(UtcDate, {
            propsData: { date: "2015-10-21T16:29:00.000000" },
            localVue,
        });
        // expect elapsed time to be 'years ago.
        expect(wrapper.text()).toBe("2015-10-21T16:29:00.000Z");
        expect(wrapper.vm.elapsedTime).toContain("years ago");
        expect(wrapper.vm.fullISO).toBe("2015-10-21T16:29:00.000Z");
        expect(wrapper.vm.parsedDate).toEqual(new Date("2015-10-21T16:29:00.000Z"));
        expect(wrapper.vm.pretty).toBe("Wednesday Oct 21st 16:29:00 2015 UTC");
    });
});
