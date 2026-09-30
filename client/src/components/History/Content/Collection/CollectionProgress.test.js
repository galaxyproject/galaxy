import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { BProgressBar } from "bootstrap-vue";
import { describe, expect, it } from "vitest";

import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

const localVue = getLocalVue();

// BProgress/BProgressBar are globally stubbed in the test setup, so the real
// `.progress`/`.bg-*` DOM classes never render -- read the value off the
// BProgressBar stub's `variant` prop instead.
function progressBarValue(wrapper, variant) {
    const bar = wrapper.findAllComponents(BProgressBar).find((b) => b.props("variant") === variant);
    return bar?.props("value");
}

describe("CollectionProgress", () => {
    let wrapper;

    it("should display the correct number of items", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            props: {
                summary: jobStateSummary,
            },
            global: localVue,
        });
        await wrapper.vm.$nextTick();
        expect(progressBarValue(wrapper, "warning")).toBe(3);
    });

    it("should correctly display states", async () => {
        const dsc = { job_state_summary: { all_jobs: 5, running: 3, failed: 1, ok: 1 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            props: {
                summary: jobStateSummary,
            },
            global: localVue,
        });
        await wrapper.vm.$nextTick();
        expect(progressBarValue(wrapper, "warning")).toBe(3);
        expect(progressBarValue(wrapper, "success")).toBe(1);
        expect(progressBarValue(wrapper, "danger")).toBe(1);
    });

    it("should update as dataset states change", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };
        let jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            props: {
                summary: jobStateSummary,
            },
            global: localVue,
        });
        await wrapper.vm.$nextTick();
        expect(progressBarValue(wrapper, "warning")).toBe(3);
        dsc["job_state_summary"]["ok"] = 2;
        dsc["job_state_summary"]["running"] = 1;
        jobStateSummary = new JobStateSummary(dsc);
        await wrapper.setProps({ summary: jobStateSummary });
        await wrapper.vm.$nextTick();
        expect(progressBarValue(wrapper, "warning")).toBe(1);
        expect(progressBarValue(wrapper, "success")).toBe(2);
    });

    it("should be visible when all jobs are queued", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, queued: 3 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            props: {
                summary: jobStateSummary,
            },
            global: localVue,
        });
        await wrapper.vm.$nextTick();
        expect(progressBarValue(wrapper, "secondary")).toBe(3);
    });
});
