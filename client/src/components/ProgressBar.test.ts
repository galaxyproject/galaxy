import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ProgressBar from "./ProgressBar.vue";

const localVue = getLocalVue();

describe("ProgressBar", () => {
    it("distinguishes completed, failed, running and waiting counts for assistive technology", () => {
        const wrapper = mount(ProgressBar, {
            props: {
                note: "2 of 10 jobs complete.",
                total: 10,
                okCount: 2,
                errorCount: 1,
                runningCount: 3,
                newCount: 4,
            },
            global: localVue,
        });

        const bars = wrapper.findAll('[role="progressbar"]');
        expect(bars.map((bar) => bar.attributes("aria-label"))).toEqual([
            "2 of 10 jobs complete. Completed",
            "2 of 10 jobs complete. Failed",
            "2 of 10 jobs complete. Running",
            "2 of 10 jobs complete. Waiting",
        ]);
        expect(bars.map((bar) => bar.attributes("aria-valuenow"))).toEqual(["2", "1", "3", "4"]);
        expect(bars.every((bar) => bar.attributes("aria-valuemax") === "10")).toBe(true);
    });
});
