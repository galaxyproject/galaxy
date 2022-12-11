import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import CollectionProgress from "./CollectionProgress";
import { JobStateSummary } from "./JobStateSummary";

const localVue = getLocalVue();

describe("CollectionProgress", () => {
    let wrapper;

    it("should display the correct number of items", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            propsData: {
                summary: jobStateSummary,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");
    });

    it("should correctly display states", async () => {
        const dsc = { job_state_summary: { all_jobs: 5, running: 3, failed: 1, ok: 1 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            propsData: {
                summary: jobStateSummary,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");
        expect(wrapper.find(".progress").find(".bg-success").attributes("aria-valuenow")).toBe("1");
        expect(wrapper.find(".progress").find(".bg-danger").attributes("aria-valuenow")).toBe("1");
    });

    it("should update as dataset states change", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, running: 3 }, populated_state: {} };
        let jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            propsData: {
                summary: jobStateSummary,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("3");
        dsc["job_state_summary"]["ok"] = 2;
        dsc["job_state_summary"]["running"] = 1;
        jobStateSummary = new JobStateSummary(dsc);
        await wrapper.setProps({ summary: jobStateSummary });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".progress").find(".bg-warning").attributes("aria-valuenow")).toBe("1");
        expect(wrapper.find(".progress").find(".bg-success").attributes("aria-valuenow")).toBe("2");
    });

    it("should be visible when all jobs are queued", async () => {
        const dsc = { job_state_summary: { all_jobs: 3, queued: 3 }, populated_state: {} };
        const jobStateSummary = new JobStateSummary(dsc);
        wrapper = mount(CollectionProgress, {
            propsData: {
                summary: jobStateSummary,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".progress").find(".bg-secondary").attributes("aria-valuenow")).toBe("3");
    });
});
