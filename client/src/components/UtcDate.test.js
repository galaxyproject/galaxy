import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { format, parseISO } from "date-fns";
import { afterEach, describe, expect, it, vi } from "vitest";

import UtcDate from "./UtcDate.vue";

enableAutoUnmount(afterEach);
afterEach(() => vi.useRealTimers());

const DATE = "2015-10-21T16:29:00.000000";

function mountDate() {
    return shallowMount(UtcDate, {
        props: { date: DATE },
        global: getLocalVue(),
    });
}

describe("UtcDate", () => {
    it("renders the default mode as an ISO date", () => {
        const wrapper = mountDate();
        expect(wrapper.text()).toBe("2015-10-21T16:29:00.000Z");
    });

    it("updates from an ISO date to elapsed time when the mode changes", async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2025-10-21T16:29:00.000Z"));
        const wrapper = mountDate();
        expect(wrapper.text()).toBe("2015-10-21T16:29:00.000Z");

        await wrapper.setProps({ mode: "elapsed" });

        expect(wrapper.text()).toBe("about 10 years ago");
        await wrapper.setProps({ mode: "pretty" });
        expect(wrapper.text()).toBe(format(parseISO("2015-10-21T16:29:00.000Z"), "eeee MMM do H:mm:ss yyyy zz"));
    });
});
