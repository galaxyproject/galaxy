import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { deleteJob } from "@/api/jobs";
import { jobsProvider } from "@/components/providers/JobProvider";

import JobsList from "./JobsList.vue";

vi.mock("@/api/jobs", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    deleteJob: vi.fn(),
}));

vi.mock("@/components/providers/JobProvider", () => ({
    jobsProvider: vi.fn(),
}));

const globalConfig = getLocalVue();

const JOBS = [
    { id: "job1", state: "running", tool_id: "cat1", update_time: "2026-01-01T00:00:00" },
    { id: "job2", state: "queued", tool_id: "cat2", update_time: "2026-01-01T00:00:00" },
];

async function mountJobsList(attachTo?: HTMLElement) {
    vi.mocked(jobsProvider).mockResolvedValue(JOBS);
    vi.mocked(deleteJob).mockResolvedValue(true);
    const wrapper = mount(JobsList as object, {
        attachTo,
        global: {
            ...globalConfig,
            stubs: {
                ...globalConfig.stubs,
                FilterMenu: true,
                FontAwesomeIcon: true,
                JobDetails: true,
                JobLock: true,
                UtcDate: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("JobsList", () => {
    it("stops only the jobs ticked in the unfinished jobs table", async () => {
        const wrapper = await mountJobsList();
        const rows = wrapper.findAll('.jobs-table tbody input[type="checkbox"]');
        expect(rows.map((row) => row.attributes("aria-label"))).toEqual(["Select job job1", "Select job job2"]);
        expect(wrapper.find("#stop-message").exists()).toBe(false);

        await rows[1]!.setValue(true);
        expect((rows[1]!.element as HTMLInputElement).checked).toBe(true);
        expect(wrapper.find('.jobs-table thead input[type="checkbox"]').element).toHaveProperty("indeterminate", true);

        await wrapper.find("#stop-message").setValue("maintenance");
        await wrapper.find("#stop-message").element.closest("form")!.dispatchEvent(new Event("submit"));
        await flushPromises();

        expect(deleteJob).toHaveBeenCalledTimes(1);
        expect(deleteJob).toHaveBeenCalledWith("job2", "maintenance");
    });

    it("unticks a job again", async () => {
        const wrapper = await mountJobsList();
        const row = wrapper.find('.jobs-table tbody input[type="checkbox"]');

        await row.setValue(true);
        expect(wrapper.find("#stop-message").exists()).toBe(true);

        await row.setValue(false);
        expect(wrapper.find("#stop-message").exists()).toBe(false);
    });

    it("reloads every unfinished job when the time cutoff is switched off", async () => {
        const wrapper = await mountJobsList();
        const toggle = wrapper.find("#show-all-running");
        expect(toggle.attributes("role")).toBe("switch");

        await toggle.setValue(true);
        await flushPromises();

        expect(vi.mocked(jobsProvider).mock.lastCall![0]).toHaveProperty("state");
        expect(wrapper.text()).toContain("Showing all unfinished jobs");
    });

    it("ticks a job without opening its details", async () => {
        // Attached, so the click runs the checkbox activation and fires change
        const wrapper = await mountJobsList(document.body);
        await wrapper.find('.jobs-table tbody input[type="checkbox"]').trigger("click");

        expect(wrapper.find("#stop-message").exists()).toBe(true);
        expect(wrapper.find(".g-table-details-row").exists()).toBe(false);
        wrapper.unmount();
    });
});
