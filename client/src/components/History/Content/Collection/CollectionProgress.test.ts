import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { BProgressBar } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

const localVue = getLocalVue();

async function mountComponent(dsc: object) {
    const jobStateSummary = new JobStateSummary(dsc);

    const wrapper = mount(CollectionProgress as object, {
        props: {
            summary: jobStateSummary,
        },
        global: localVue,
    });

    await flushPromises();

    return wrapper;
}

// BProgress/BProgressBar are globally stubbed in the test setup, so the real
// `.progress`/`.bg-*` DOM classes never render -- read the value off the
// BProgressBar stub's `variant` prop instead.
function progressBarValue(wrapper: VueWrapper<any>, variant: string) {
    const bar = wrapper.findAllComponents(BProgressBar).find((b) => b.props("variant") === variant);
    return bar?.props("value");
}

describe("CollectionProgress", () => {
    it("should display the correct number of items", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(progressBarValue(wrapper, "warning")).toBe(3);
    });

    it("should correctly display states", async () => {
        const dsc = { job_state_summary: { all_jobs: 5, running: 3, failed: 1, ok: 1 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(progressBarValue(wrapper, "warning")).toBe(3);
        expect(progressBarValue(wrapper, "success")).toBe(1);
        expect(progressBarValue(wrapper, "danger")).toBe(1);
    });

    it("should update as dataset states change", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3, ok: 0 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(progressBarValue(wrapper, "warning")).toBe(3);

        dsc["job_state_summary"]["ok"] = 2;
        dsc["job_state_summary"]["running"] = 1;

        await wrapper.setProps({ summary: new JobStateSummary(dsc) });

        expect(progressBarValue(wrapper, "warning")).toBe(1);
        expect(progressBarValue(wrapper, "success")).toBe(2);
    });

    it("should be visible when all jobs are queued", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, queued: 3 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(progressBarValue(wrapper, "secondary")).toBe(3);
    });
});
