import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

const localVue = getLocalVue();

async function mountComponent(dsc: object) {
    const jobStateSummary = new JobStateSummary(dsc);

    const wrapper = mount(CollectionProgress as object, {
        propsData: {
            summary: jobStateSummary,
        },
        localVue,
    });

    await flushPromises();

    return wrapper;
}

describe("CollectionProgress", () => {
    it("should display the correct number of items", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");
    });

    it("should correctly display states", async () => {
        const dsc = { job_state_summary: { all_jobs: 5, running: 3, failed: 1, ok: 1 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");
        expect(wrapper.find(".progress").find(".bg-success").attributes("aria-valuenow")).toBe("1");
        expect(wrapper.find(".progress").find(".bg-danger").attributes("aria-valuenow")).toBe("1");
    });

    it("should update as dataset states change", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3, ok: 0 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");

        dsc["job_state_summary"]["ok"] = 2;
        dsc["job_state_summary"]["running"] = 1;

        await wrapper.setProps({ summary: new JobStateSummary(dsc) });

        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("1");
        expect(wrapper.find(".progress").find(".bg-success").attributes("aria-valuenow")).toBe("2");
    });

    it("should be visible when all jobs are queued", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, queued: 3 }, populated_state: {} };

        const wrapper = await mountComponent(dsc);

        expect(wrapper.find(".progress").find(".bg-secondary").attributes("aria-valuenow")).toBe("3");
    });
});
