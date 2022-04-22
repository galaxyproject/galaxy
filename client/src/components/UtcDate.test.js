import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import UtcDate from "./UtcDate.vue";

describe("UTCDate component", () => {
    const localVue = getLocalVue();

    it("Loads a date in default mode, computeds work", () => {
        const wrapper = shallowMount(UtcDate, {
            propsData: { date: "2015-10-21T16:29:00.000000" },
            localVue,
        });
        // expect elapsed time to be years ago.
        expect(wrapper.text()).toBe("2015-10-21T16:29:00Z");
        expect(wrapper.vm.elapsedTime).toContain("years ago");
        expect(wrapper.vm.fullDate).toBe("2015-10-21T16:29:00Z");
        expect(wrapper.vm.formattedDate).toBe("2015-10-21T16:29:00.000000");
        expect(wrapper.vm.pretty).toBe("Wednesday Oct 21st 4:29:00 2015 UTC");
    });
});
