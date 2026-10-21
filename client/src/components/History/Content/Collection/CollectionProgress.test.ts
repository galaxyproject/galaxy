import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

type JobStates = Record<string, number>;

function summaryOf(jobStates: JobStates) {
    return new JobStateSummary({ job_state_summary: jobStates, populated_state: {} });
}

function mountWithJobs(jobStates: JobStates) {
    return mount(CollectionProgress, {
        props: { summary: summaryOf(jobStates) },
        global: localVue,
    });
}

/** Rendered progress bars as `{ <bootstrap variant>: <aria-valuenow> }`. */
function renderedBars(wrapper: VueWrapper) {
    return Object.fromEntries(
        wrapper.findAll(".progress .progress-bar").map((bar) => {
            const variant = bar.classes().find((name) => name.startsWith("bg-"))!;
            return [variant.replace("bg-", ""), bar.attributes("aria-valuenow")];
        }),
    );
}

describe("CollectionProgress", () => {
    it.each<{ name: string; jobStates: JobStates; bars: Record<string, string> }>([
        {
            name: "running jobs as a warning bar",
            jobStates: { all_jobs: 3, running: 3 },
            bars: { warning: "3" },
        },
        {
            name: "failed, ok and running jobs as separate bars",
            jobStates: { all_jobs: 5, running: 3, failed: 1, ok: 1 },
            bars: { danger: "1", success: "1", warning: "3" },
        },
        {
            name: "queued jobs as a secondary bar",
            jobStates: { all_jobs: 3, queued: 3 },
            bars: { secondary: "3" },
        },
    ])("shows $name", ({ jobStates, bars }) => {
        const wrapper = mountWithJobs(jobStates);

        expect(renderedBars(wrapper)).toEqual(bars);
    });

    it("updates the bars as job states change", async () => {
        const wrapper = mountWithJobs({ all_jobs: 3, running: 3, ok: 0 });
        expect(renderedBars(wrapper)).toEqual({ warning: "3" });

        await wrapper.setProps({ summary: summaryOf({ all_jobs: 3, running: 1, ok: 2 }) });

        expect(renderedBars(wrapper)).toEqual({ success: "2", warning: "1" });
    });

    it("hides the progress bar once every job is terminal", () => {
        const wrapper = mountWithJobs({ all_jobs: 2, ok: 2 });

        expect(wrapper.find(".progress").exists()).toBe(false);
    });
});
